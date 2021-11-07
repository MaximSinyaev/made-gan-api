from torch._C import device
from app.image_generation.image_generator import ImageGeneratorGAN

if __name__ == "__main__":
    gan = ImageGeneratorGAN()
    gan.generate_picture("Squirel family", device="cuda:3")
