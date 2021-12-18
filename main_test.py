from torch._C import device
from app.image_generation.image_generator import ImageGeneratorGAN

if __name__ == "__main__":
    gan = ImageGeneratorGAN(device="cuda:5")
    gan.generate_picture("Squirel family", width=256, height=256)

