import asyncio
from pysnmp.hlapi.v3arch.asyncio import *
import datetime

def oid_tuple(oid_str):
    """Convert OID string to tuple of integers for proper comparison"""
    return tuple(int(x) for x in oid_str.split('.'))

async def safe_snmp_walk(host):
    """
    Walk only the relevant OIDs for memory, disk, and CPU.
    Returns a dict {oid: value}.
    """
    snmpEngine = SnmpEngine()
    transport = await UdpTransportTarget.create((host, 161))
    
    user_data = UsmUserData(
        userName="sentinel",
        authKey="sentinelXPWD",
        privKey="sentinelXPWD",
        authProtocol=usmHMAC384SHA512AuthProtocol,
        privProtocol=usmAesCfb128Protocol
    )
    base_oids = [
        "1.3.6.1.2.1.25.2.3.1",   # hrStorageTable (memory & disk)
        "1.3.6.1.2.1.25.3.3.1.2",  # hrProcessorLoad (CPU)
        "1.3.6.1.4.1.2021.10.1.3"
    ]

    results = {}

    for base_oid in base_oids:
        current_oid = ObjectIdentity(base_oid)
        last_oid = None
        
        

        while True:
            errorIndication, errorStatus, errorIndex, varBinds = await next_cmd(
                snmpEngine,
                user_data,
                transport,
                ContextData(),
                ObjectType(current_oid),
                lexicographicMode=True,
            )

            if errorIndication or errorStatus or not varBinds:
                break

            stop_walk = False  # <--- flag to break the while loop

            for varBind in varBinds:
                oid, value = str(varBind[0]), varBind[1].prettyPrint()

                if not oid.startswith(base_oid):
                    stop_walk = True
                    break

                if last_oid and oid_tuple(oid) <= oid_tuple(last_oid):
                    stop_walk = True
                    break

                last_oid = oid
                results[oid] = value
                current_oid = ObjectIdentity(oid)

            if stop_walk:
                break

    snmpEngine.close_dispatcher()
    return results

async def get_system_info(host):
    # Walk HOST-RESOURCES-MIB
    data = await safe_snmp_walk(host)

    memory = {}
    disk = {}
    cpu = {}

    for oid, value in data.items():
        parts = oid.split('.')
        # hrStorageTable: 1.3.6.1.2.1.25.2.3.1
        if oid.startswith("1.3.6.1.2.1.25.2.3.1"):
            column = int(parts[-2])
            row = parts[-1]
            if row not in memory and row not in disk:
                row_dict = {}
            else:
                row_dict = memory.get(row, disk.get(row, {}))

            if column == 3:
                row_dict['descr'] = value
            elif column == 4:
                row_dict['alloc_unit'] = int(value)
            elif column == 5:
                row_dict['size'] = int(value)
            elif column == 6:
                row_dict['used'] = int(value)

            # classify memory vs disk based on descr
            descr = row_dict.get('descr', '').lower()
            if 'memory' in descr or 'ram' in descr:
                memory[row] = row_dict
            else:
                disk[row] = row_dict

    # CPU: hrProcessorLoad
    cpu_load_oids = {oid: value for oid, value in data.items() if oid.startswith("1.3.6.1.2.1.25.3.3.1.2")}
    if cpu_load_oids:
        cpu_percentages = [int(v) for v in cpu_load_oids.values()]
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        cpu['per_core'] = cpu_percentages
        cpu['average'] = avg_cpu
    load_oids = {
        "1min": "1.3.6.1.4.1.2021.10.1.3.1",
        "5min": "1.3.6.1.4.1.2021.10.1.3.2",
        "15min": "1.3.6.1.4.1.2021.10.1.3.3",
    }
    loads = {k: data.get(oid) for k, oid in load_oids.items()}
    return memory, disk, cpu, loads

async def main():
    host = "192.168.0.38"
    memory, disk, cpu, loads = await get_system_info(host)

    print("\nMemory Usage:")
    for row, info in memory.items():
        used_bytes = info.get('used', 0) * info.get('alloc_unit', 1)
        total_bytes = info.get('size', 0) * info.get('alloc_unit', 1)
        print(f"{info.get('descr','unknown')}: {used_bytes/1024/1024:.1f} MB used / {total_bytes/1024/1024:.1f} MB total")

    print("\nDisk Usage:")
    for row, info in disk.items():
        used_bytes = info.get('used', 0) * info.get('alloc_unit', 1)
        total_bytes = info.get('size', 0) * info.get('alloc_unit', 1)
        print(f"{info.get('descr','unknown')}: {used_bytes/1024/1024:.1f} MB used / {total_bytes/1024/1024:.1f} MB total")

    print("\nCPU Load:")
    if cpu:
        print(f"Per-core: {cpu.get('per_core', [])}")
        print(f"Average: {cpu.get('average', 0):.1f}%")
    else:
        print("No CPU info available via hrProcessorLoad")

    print("Load averages:", str(loads))


first = datetime.datetime.now()
asyncio.run(main())
second = datetime.datetime.now()
print(f"That took {str(second-first)} seconds")