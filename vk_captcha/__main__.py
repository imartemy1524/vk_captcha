from .solver import VkCaptchaSolver
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="VK Captcha decoder")

    parser.add_argument("-url", dest="url", required=True)
    parser.add_argument("-minimum-accuracy", dest="minimum_accuracy", default=0.3, type=float)
    parser.add_argument("-repeat-count", dest="repeat_count", default=10, type=int)

    args = parser.parse_args()
    return {
        "url": args.url,
        "minimum_accuracy": args.minimum_accuracy,
        "repeat_count": args.repeat_count,
    }


if __name__ == '__main__':
    ans = VkCaptchaSolver().solve(**parse_args())
    print(" ".join(map(str, ans)))
