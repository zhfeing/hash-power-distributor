from hash_power_client import HashPowerClient


if __name__ == "__main__":
    slave = HashPowerClient(
        server_address=("zjlab-1", 13105),
    )
    print(slave.get_system_info())
    # print(slave.allocate_gpus(num_gpus=2, exclusive=False, mem_size=10e9))
    # print(slave.allocate_gpus(num_gpus=2, exclusive=True))
    print(slave.release_gpus(["025beaf24a6311eab886f40270a36b56", "031395104a6311eab886f40270a36b56"]))

