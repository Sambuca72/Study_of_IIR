import csv
from icmplib import multiping


def get_ping(domains):
    return multiping(domains, count=4, interval=0.9, timeout=1.5)

def save_csv(filename, ping_res):
    titles = ["Доменчик", "Время(мс)", "Потери(%)", "min.RTT", "max.RTT", "Jitter"]

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(titles)
            
            for host in ping_res:
                writer.writerow([
                       host.address,
                    f"{host.avg_rtt:.1f}",
                    f"{host.packet_loss * 100:.1f}",
                    f"{host.min_rtt:.1f}",
                    f"{host.max_rtt:.1f}",
                    f"{host.jitter:.1f}"])

    except PermissionError:
        print("Записи в csv не быть, дом гореть и т.д и т.п")

def main():
    domains = ["pornhub.com", "deepseek.com", "github.com", "table.nsu.ru", "mail.google.com",
               "google.com", "yandex.ru", "telegram.com", "grok.com", "genius.com"]
    output = "result.csv"

    ping_result = get_ping(domains)
    print(f"Получено доменов: {len(ping_result)}, всё ок: ")

    save_csv(output, ping_result)

if __name__ == "__main__":
    main()

# black, flake8, linter, precommit




