# Hash Power Distributor

## Server Usage

To install service, run

```sh
./install.sh install --python=/absolute/path/to/python
```

and the distributer daemon will start automatically. 

To uninstall service, run

```sh
./install.sh uninstall
```

and the distributer daemon will stop automatically. 

## Server Requirement

1. `tornado` latest version
2. `nvidia-ml-py3` latest version
3. `cupy` latest version

## Client Usage

To use client in python, firstly you should create client object:

```python
slave = HashPowerClient(server_address=("localhost", 13105))
```

We offer 3 sync APIs for you to manage GPUs:
`get_system_info`, `allocate_gpus` and `release_gpus`.

## Client Requirement

`tornado` is all you needed.
