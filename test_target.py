import time


def compute():
    total = 0
    for i in range(5):
        total += i
        time.sleep(0.1)
    return total


if __name__ == "__main__":
    result = compute()
    print(f"Resultado: {result}")