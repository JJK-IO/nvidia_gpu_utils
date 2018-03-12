import os
import subprocess
import time


class GPU:
    env = os.environ.copy()
    env['GPU_FORCE_64BIT_PTR'] = '0'
    env['GPU_MAX_HEAP_SIZE'] = '100'
    env['GPU_USE_SYNC_OBJECTS'] = '1'
    env['GPU_MAX_ALLOC_PERCENT'] = '100'
    env['GPU_SINGLE_ALLOC_PERCENT'] = '100'
    env['DISPLAY'] = ':0'

    def __init__(self, id, name, uuid):
        self.id = id
        self.name = name
        self.uuid = uuid

    def temperature(self):
        nvidia_cmd = [
            'nvidia-smi',
            '-q',  # Query devices
            '-i', self.id,  # GPU id
            '-d', 'TEMPERATURE'  # GPU temp
        ]
        nvidia_process = subprocess.Popen(
            nvidia_cmd,
            stdout=subprocess.PIPE,
            env=GPU.env
        )

        grep_cmd = ['grep', 'GPU Current']
        grep_process = subprocess.Popen(
            grep_cmd,
            stdin=nvidia_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        )

        awk_cmd = ['awk', '{print $5}']
        awk_process = subprocess.Popen(
            awk_cmd,
            stdin=grep_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        )

        return float(awk_process.communicate()[0].decode("utf-8").strip())

    def set_fan_speed(self, percent):
        nvidia_cmd = [
            'nvidia-settings -a [gpu:{}]/GPUFanControlState=1 -a [fan:{}]/GPUTargetFanSpeed={}'.format(
                self.id,
                self.id,
                percent
            )
        ]
        nvidia_process = subprocess.Popen(
            nvidia_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        ).communicate()[0].decode("utf-8").strip()
        print(nvidia_process)

    def set_gpu_clock_offset(self, offset):
        # +180 seems standard for 1080tis
        nvidia_cmd = [
            'nvidia-settings -a [gpu:{}]/GPUGraphicsClockOffset[3]={}'.format(self.id, offset)
        ]
        nvidia_process = subprocess.Popen(
            nvidia_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        ).communicate()[0].decode("utf-8").strip()
        print(nvidia_process)

    def set_gpu_memory_rate_offset(self, offset):
        # Offset of -250 have been promising for GPU Mining
        nvidia_cmd = [
            'nvidia-settings',
            '-a', '[gpu:{}]/GPUMemoryTransferRateOffset[3]={}'.format(self.id, offset)
        ]
        nvidia_process = subprocess.Popen(
            nvidia_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        ).communicate()[0].decode("utf-8").strip()
        print(nvidia_process)

    def power_limit(self, default=False):
        nvidia_cmd = [
            'nvidia-smi',
            '-q',  # Query devices
            '-i', self.id,  # GPU id
            '-d', 'POWER'  # GPU POWER
        ]
        nvidia_process = subprocess.Popen(
            nvidia_cmd,
            stdout=subprocess.PIPE,
            env=GPU.env
        )

        grep_cmd = ['grep', 'Enforced']
        if default:
            grep_cmd = ['grep', 'Default']

        grep_process = subprocess.Popen(
            grep_cmd,
            stdin=nvidia_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        )

        awk_cmd = ['awk', '{print $5}']
        awk_process = subprocess.Popen(
            awk_cmd,
            stdin=grep_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        )

        return awk_process.communicate()[0].decode("utf-8").strip()

    def set_power_limit(self, pl):
        nvidia_cmd = [
            'nvidia-smi', '-i', self.id, '-pl', pl]
        nvidia_process = subprocess.Popen(
            nvidia_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        ).communicate()[0].decode("utf-8").strip()
        print(nvidia_process)

    def __str__(self):
        return "ID: {} Name: {}".format(self.id, self.name)

    def __repr__(self):
        return "<GPU ID: {} Name: {}>".format(self.id, self.name)

    @staticmethod
    def x_server_live():
        process_cmd = ['ps', '-e']
        process_process = subprocess.Popen(
            process_cmd,
            stdout=subprocess.PIPE,
            env=GPU.env
        )

        grep_cmd = ['grep', 'Xorg']
        grep_process = subprocess.Popen(
            grep_cmd,
            stdin=process_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GPU.env
        )
        if grep_process.communicate()[0].decode("utf-8").strip() != "":
            return True
        return False

    @staticmethod
    def start_x():
        x_cmd = ['X', ':0', '&']
        subprocess.run(x_cmd)
        time.sleep(3)
        export_display_cmd = ['export', 'DISPLAY=:0']
        subprocess.run(export_display_cmd)
        time.sleep(1)

    @staticmethod
    def enable_persistence():
        """
        nvidia-xconfig --allow-empty-initial-configuration --enable-all-gpus --cool-bits=28 --separate-x-screens
        nvidia-smi -pm ENABLED
        """
        nvidia_xconfig_cmd = [
            'nvidia-xconfig',
            '--allow-empty-initial-configuration',
            '--enable-all-gpus',
            '--cool-bits=28',
            '--separate-x-screens'
        ]
        subprocess.run(nvidia_xconfig_cmd)
        persitence_cmd = [
            'nvidia-smi',
            '-pm', 'ENABLED'
        ]
        subprocess.run(persitence_cmd)

    @staticmethod
    def load_gpus():
        gpu_list = []
        list_gpu_command = ['nvidia-smi', '-L']
        list_gpu_process = subprocess.Popen(list_gpu_command, stdout=subprocess.PIPE)
        for gpu in list_gpu_process.communicate()[0].decode("utf-8").strip().split("\n"):
            gpu_id = gpu.split(":")[0].split(" ")[1]
            gpu_name = gpu.split(":")[1].split("(")[0].strip()
            gpu_uuid = gpu.split(":")[2].strip().replace(")", "")
            gpu_list.append(GPU(gpu_id, gpu_name, gpu_uuid))
        return gpu_list


if __name__ == "__main__":
    if not GPU.x_server_live():
        GPU.start_x()

    print(GPU.env)

    GPU.enable_persistence()

    gpus = GPU.load_gpus()

    gpus[0].power_limit(240)
    gpus[1].power_limit(250)

    while True:
        for gpu in gpus:
            gpu_temp = gpu.temperature()
            if gpu_temp >= 75:
                print("GPU {}: Temp: {}, setting fan's to 90%".format(gpu.id, gpu_temp))
                gpu.set_fan_speed(90)
            elif gpu_temp >= 70:
                print("GPU {}: Temp: {}, setting fan's to 75%".format(gpu.id, gpu_temp))
                gpu.set_fan_speed(75)
            elif gpu_temp >= 65:
                print("GPU {}: Temp: {}, setting fan's to 70%".format(gpu.id, gpu_temp))
                gpu.set_fan_speed(70)
            elif gpu_temp >= 60:
                print("GPU {}: Temp: {}, setting fan's to 60%".format(gpu.id, gpu_temp))
                gpu.set_fan_speed(60)
            elif gpu_temp >= 40:
                print("GPU {}: Temp: {}, setting fan's to 55%".format(gpu.id, gpu_temp))
                gpu.set_fan_speed(55)
            else:
                print("GPU {}: Temp: {}, setting fan's to 20%".format(gpu.id, gpu_temp))
                gpu.set_fan_speed(20)
        time.sleep(5)
