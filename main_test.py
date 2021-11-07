from torch._C import device
from app.image_generation.image_generator import ImageGeneratorGAN

if __name__ == "__main__":
    gan = ImageGeneratorGAN(device="cuda:3")
    gan.generate_picture("Squirel family")

