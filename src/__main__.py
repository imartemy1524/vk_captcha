from .solver import VkCaptchaSolver
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Captcha decoder")

    parser.add_argument("-url", dest="url", required=True)
    parser.add_argument("-minimum-accuracy", dest="minimum_accuracy", default=0.3, type=float)
    parser.add_argument("-repeat-count", dest="repeat_accuracy", default=10, type=int)

    args = parser.parse_args()
    return {
        "url": args.url,
        "minimum_accuracy": args.minimum_accuracy,
        "repeat_accuracy": args.repeat_accuracy,
    }


if __name__ == '__main__':
    VkCaptchaSolver().solve(**parse_args())
