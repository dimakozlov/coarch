import sys
import csv
import math
import hashlib
import argparse
import statistics
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass

import yaml


SAMPLE_MAX = 255


def psnr2mse(psnr: float) -> float:
    return SAMPLE_MAX * SAMPLE_MAX / pow(10, psnr / 10)

def mse2psnr(mse: float) -> float:
    return 10 * math.log10(SAMPLE_MAX * SAMPLE_MAX / mse)

class Metrics:
    def __init__(self):
        self.codec: str = ''
        self.stream: str = ''

        self.psnr_y = defaultdict(list)
        self.psnr_u = defaultdict(list)
        self.psnr_v = defaultdict(list)

        self.frame_size = defaultdict(list)

    @property
    def empty(self):
        return not self.codec


@dataclass
class Tool:
    label: str
    cmd: str
    qp: bool = False

    @property
    def md5(self):
        m = hashlib.md5()
        m.update(self.cmd.replace(' ', '').encode('utf-8', errors='replace'))

        return m.hexdigest()


codec2tool = {}

def load_csv(src: Path) -> Metrics:
    m = Metrics()
    parts = src.name.split('_')
    m.stream = '_'.join(parts[:-1])

    with src.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            m.codec = row['Codec']

            br_or_qp = row['Bitrate'] if 'Bitrate' in row else row['QP']
            m.psnr_y[br_or_qp].append(float(row['PSNR-Y']))
            m.psnr_u[br_or_qp].append(float(row['PSNR-U']))
            m.psnr_v[br_or_qp].append(float(row['PSNR-V']))
            m.frame_size[br_or_qp].append(int(row['Bytes']))

    return m

def generate_yamls(m: Metrics) -> None:
    frame_rate = 30
    for br in m.psnr_y.keys():
        mse_y = [psnr2mse(psnr) for psnr in m.psnr_y[br]]
        mse_u = [psnr2mse(psnr) for psnr in m.psnr_u[br]]
        mse_v = [psnr2mse(psnr) for psnr in m.psnr_v[br]]

        frames = len(mse_y)
        main_data = {
            'FPS': 22.05,
            'extra': {
                'CPU_percent': 100,
                'CPU_usage': '100',
                'FPS': 60,
                'encode_time': 0,
                'frames': frames
            },
            'metrics': {
                'PSNR': {
                    'Y': mse2psnr(statistics.mean(mse_y)),
                    'U': mse2psnr(statistics.mean(mse_u)),
                    'V': mse2psnr(statistics.mean(mse_v))
                },
                'APSNR': {
                    'Y': statistics.mean(m.psnr_y[br]),
                    'U': statistics.mean(m.psnr_u[br]),
                    'V': statistics.mean(m.psnr_v[br])
                }
            },
            'file_size': sum(m.frame_size[br]),
            'platform': {
                'CPU': 'Intel64 Family 6 Model 141 Stepping 0', 'OS': 'Microsoft Windows 10 Pro 10.0.19042', 'hostname': 'gtapc', 'power_plan': 'Balanced', 'video_driver': 'master-7524'
            },
            'real_bitrate': sum(m.frame_size[br]) / frames * frame_rate * 8,
            'tool_command': codec2tool[m.codec].cmd
        }

        root = Path('.cache')

        tool = codec2tool.get(m.codec)
        if tool is None:
            sys.exit(f"There is no tool with '{m.codec}' codec defined in the EDC config")

        tool_folder = f'{tool.label}.{tool.md5}'
        (root / tool_folder).mkdir(parents=True, exist_ok=True)
        main = root / tool_folder / f'{br}.{m.stream}.yuv.yaml'
        with main.open('wt+') as f:
            yaml.dump(main_data, f)

        details_data = []
        for psnr_y, psnr_u, psnr_v, frame_size in zip(m.psnr_y[br], m.psnr_u[br], m.psnr_v[br], m.frame_size[br]):
            details_data.append(
                {
                    'PSNR': {
                        'Y': psnr_y,
                        'U': psnr_u,
                        'V': psnr_v
                    },
                    'frame_size': frame_size
                }
            )

        details = root / tool_folder / f'{br}.{m.stream}.yuv.details.yaml'
        with details.open('wt+') as f:
            yaml.dump(details_data, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f"COnvertor of ARCH data")
    parser.add_argument('config', nargs='?', default='edc.yaml',
                        help='configuration file in yaml format')

    args = parser.parse_args()
    config = Path(args.config)

    if not config.exists():
        sys.exit(f"Can't open configuration file: {config}")

    with config.open() as f:
        cfg = yaml.safe_load(f)

    if 'tools' not in cfg:
        sys.exit(f"There are no 'tools' section in the configuration file: {config}")

    for tool in cfg['tools']:
        if 'codec' not in tool:
            continue

        codec = tool['codec']
        label = tool['label']
        if 'command-line' in tool:
            codec2tool[codec] = Tool(label, tool['command-line'], qp=False)
        elif 'command-line-cqp' in tool:
            codec2tool[codec] = Tool(label, tool['command-line'], qp=True)

    if not codec2tool:
        sys.exit(f"There are no tools in the tools section with 'codec' attribute")

    for csv_file in Path('data').glob('*.csv'):
        m = load_csv(csv_file)

        if not m.empty:
            print(csv_file.name)
            generate_yamls(m)


