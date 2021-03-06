import logging
import argparse
import os


from PIL import Image
import PIL
import torch
from torch import optim
from torch.nn import functional as F
from torchvision import transforms
from torchvision.transforms import functional as TF
from clip import clip
import kornia.augmentation as K
import numpy as np
import imageio
from PIL import ImageFile, Image


# from app.configs.consts import model_names
from .utils import *

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger()

torch.set_num_threads(6)
ImageFile.LOAD_TRUNCATED_IMAGES = True


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ImageGeneratorGAN(object, metaclass=Singleton):
    model_names = {
        "vqgan_imagenet_f16_16384": "ImageNet 16384",
        "vqgan_imagenet_f16_1024": "ImageNet 1024",
        "vqgan_openimages_f16_8192": "OpenImages 8912",
        "wikiart_1024": "WikiArt 1024",
        "wikiart_16384": "WikiArt 16384",
        "coco": "COCO-Stuff",
        "faceshq": "FacesHQ",
        "sflckr": "S-FLCKR",
    }
    clip_model='ViT-B/32'

    def __init__(
        self, model_name="vqgan_imagenet_f16_16384", seed=-1, device=None,
        cutn=32,
        cut_pow=1.0,
    ) -> None:
        if device is None:
            self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        LOG.info(f"Using device: {self.device}")

        self.model_name = self.model_names[model_name]
        assert model_name in self.model_names
        self.base_model = model_name
        LOG.info(f'Using model {self.base_model}')

        vqgan_config=f"models/{self.base_model}.yaml"
        vqgan_checkpoint=f"models/{self.base_model}.ckpt"

        # Models init
        self.model = load_vqgan_model(vqgan_config, vqgan_checkpoint).to(
            self.device
        )
        self.perceptor = (
            clip.load(self.clip_model, jit=False, device=self.device)[0]
            .eval()
            .requires_grad_(False)
            .to(self.device)
        )
        cut_size = self.perceptor.visual.input_resolution

        self.f = 2 ** (self.model.decoder.num_resolutions - 1)
        self.make_cutouts = MakeCutouts(cut_size, cutn, cut_pow=cut_pow)

        self.normalize = transforms.Normalize(
            mean=[0.48145466, 0.4578275, 0.40821073],
            std=[0.26862954, 0.26130258, 0.27577711],
        )

    def generate_picture(
        self,
        texts,
        filename, #task id
        init_image="None",
        target_images=None,
        width=256,
        height=256,
        seed=-1,
        max_iterations=500,
        path="results",
    ):
        if not isinstance(filename, str):
            filename = str(filename)
        args = self.set_model_params(
            texts, init_image, target_images, width, height, seed
        )
        LOG.info(args)

        toksX, toksY = args.size[0] // self.f, args.size[1] // self.f
        sideX, sideY = toksX * self.f, toksY * self.f

        if args.vqgan_checkpoint == "vqgan_openimages_f16_8192.ckpt":
            e_dim = 256
            n_toks = self.model.quantize.n_embed
            z_min = self.model.quantize.embed.weight.min(dim=0).values[
                None, :, None, None
            ]
            z_max = self.model.quantize.embed.weight.max(dim=0).values[
                None, :, None, None
            ]
        else:
            e_dim = self.model.quantize.e_dim
            n_toks = self.model.quantize.n_e
            z_min = self.model.quantize.embedding.weight.min(dim=0).values[
                None, :, None, None
            ]
            z_max = self.model.quantize.embedding.weight.max(dim=0).values[
                None, :, None, None
            ]

        if args.init_image:
            if "http" in args.init_image:
                img = Image.open(urlopen(args.init_image))
            else:
                img = Image.open(args.init_image)
            pil_image = img.convert("RGB")
            pil_image = pil_image.resize((sideX, sideY), Image.LANCZOS)
            pil_tensor = TF.to_tensor(pil_image)
            z, *_ = self.model.encode(pil_tensor.to(self.device).unsqueeze(0) * 2 - 1)
        else:
            one_hot = F.one_hot(
                torch.randint(n_toks, [toksY * toksX], device=self.device), n_toks
            ).float()
            if args.vqgan_checkpoint == "vqgan_openimages_f16_8192.ckpt":
                z = one_hot @ self.model.quantize.embed.weight
            else:
                z = one_hot @ self.model.quantize.embedding.weight
            z = z.view([-1, toksY, toksX, e_dim]).permute(0, 3, 1, 2)
            z = torch.rand_like(z) * 2

        z_orig = z.clone()
        z.requires_grad_(True)
        opt = optim.Adam([z], lr=args.step_size)

        pMs = []
        for prompt in args.prompts:
            txt, weight, stop = parse_prompt(prompt)
            embed = self.perceptor.encode_text(
                clip.tokenize(txt).to(self.device)
            ).float()
            pMs.append(Prompt(embed, weight, stop).to(self.device))

        for prompt in args.image_prompts:
            path, weight, stop = parse_prompt(prompt)
            img = Image.open(path)
            pil_image = img.convert("RGB")
            img = resize_image(pil_image, (sideX, sideY))
            batch = self.make_cutouts(TF.to_tensor(img).unsqueeze(0).to(self.device))
            embed = self.perceptor.encode_image(self.normalize(batch)).float()
            pMs.append(Prompt(embed, weight, stop).to(self.device))

        for seed, weight in zip(args.noise_prompt_seeds, args.noise_prompt_weights):
            gen = torch.Generator().manual_seed(seed)
            embed = torch.empty([1, self.perceptor.visual.output_dim]).normal_(
                generator=gen
            )
            pMs.append(Prompt(embed, weight).to(self.device))

        global i
        i = 0
        try:
            while True:
                self.train(
                    i,
                    opt,
                    z,
                    z_min,
                    z_max,
                    self.perceptor,
                    args,
                    z_orig,
                    pMs,
                    filename,
                    path,
                )
                LOG.info(f'Epoch {i} done')
                if i == max_iterations:
                    lossAll = self.ascend_txt(z, self.perceptor, args, z_orig, pMs)
                    pil_image = self.checkin(i, lossAll, z, args, filename, path)
                    break
                i += 1
        except KeyboardInterrupt:
            pass

        return pil_image

    def set_model_params(self, texts, init_image, target_images, width, height, seed):
        if seed is None or seed == -1:
            seed = torch.seed()
        torch.manual_seed(seed)

        texts = [phrase.strip() for phrase in texts.split("|")]
        assert len(texts) > 0  # Text can not be empty
        assert texts != [""]  # String must have > 0 characters
        LOG.info(f"Using texts: {texts}")

        if init_image == "None":
            init_image = None
        if target_images == "None" or not target_images:
            target_images = []
        else:
            target_images = target_images.split("|")
            target_images = [image.strip() for image in target_images]
            LOG.info("Using image prompts:", target_images)

        args = argparse.Namespace(
            prompts=texts,
            image_prompts=target_images,
            noise_prompt_seeds=[],
            noise_prompt_weights=[],
            size=[width, height],
            init_image=init_image,
            init_weight=0.0,
            clip_model="ViT-B/32",
            vqgan_config=f"models/{self.base_model}.yaml",
            vqgan_checkpoint=f"models/{self.base_model}.ckpt",
            step_size=0.1,
            cutn=32,
            cut_pow=1.0,
            # display_freq=images_interval,
            seed=seed,
        )
        return args

    def synth(self, z, args):
        if args.vqgan_checkpoint == "vqgan_openimages_f16_8192.ckpt":
            z_q = vector_quantize(
                z.movedim(1, 3), self.model.quantize.embed.weight
            ).movedim(3, 1)
        else:
            z_q = vector_quantize(
                z.movedim(1, 3), self.model.quantize.embedding.weight
            ).movedim(3, 1)
        return clamp_with_grad(self.model.decode(z_q).add(1).div(2), 0, 1)

    @torch.no_grad()
    def checkin(self, i, losses, z, args, filename, path):
        if not os.path.exists(path):
            os.makedirs(path)
        losses_str = ", ".join(f"{loss.item():g}" for loss in losses)
        LOG.info(f"i: {i}, loss: {sum(losses).item():g}, losses: {losses_str}")
        out = self.synth(z, args)
        pil_image = TF.to_pil_image(out[0].cpu())


        pil_image.save(f"{path}/{filename}.png")

        return pil_image

        

    def ascend_txt(self, z, perceptor, args, z_orig, pMs):
        global i
        out = self.synth(z, args)
        iii = perceptor.encode_image(self.normalize(self.make_cutouts(out))).float()

        result = []

        if args.init_weight:
            result.append(
                F.mse_loss(z, torch.zeros_like(z_orig))
                * ((1 / torch.tensor(i * 2 + 1)) * args.init_weight)
                / 2
            )
        for prompt in pMs:
            result.append(prompt(iii))
        img = np.array(
            out.mul(255).clamp(0, 255)[0].cpu().detach().numpy().astype(np.uint8)
        )[:, :, :]
        img = np.transpose(img, (1, 2, 0))
        # imageio.imwrite("./results/" + str(i) + ".png", np.array(img))

        return result

    def train(
        self,
        i,
        opt,
        z,
        z_min,
        z_max,
        perceptor,
        args,
        z_orig,
        pMs,
        filename=None,
        path="./results",
    ):
        opt.zero_grad()
        lossAll = self.ascend_txt(z, perceptor, args, z_orig, pMs)
        # if i % args.display_freq == 0 and i != 0:
        #     self.checkin(
        #         i, lossAll, z, args, filename=filename or "progress.png", path=path
        #     )

        loss = sum(lossAll)
        loss.backward()
        opt.step()
        with torch.no_grad():
            z.copy_(z.maximum(z_min).minimum(z_max))
