from scapy.all import IP, ICMP, send
import time

def send_ipv4_packet():
    print("Send IPv4 packet...")
    packet = IP(dst="8.8.8.8") / ICMP() / "Hello IPv4"
    send(packet, verbose=False)
    print("IPv4 packet sent")

if __name__ == "__main__":
    try:
        send_ipv4_packet()
        time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")

# docker exec -it ipv6_node_1 ping6 2001:db8:1::11