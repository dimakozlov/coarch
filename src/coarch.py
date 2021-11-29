import csv
import math
import hashlib
import statistics
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass, field
from sys import platform

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

@dataclass
class Tool:
    label: str
    cmd: str

    @property
    def md5(self):
        m = hashlib.md5()
        m.update(self.cmd.replace(' ', '').encode('utf-8', errors='replace'))

        return m.hexdigest()


codec2tool = {
    'x264Fast': Tool('x264-fast-arc', 'x264 --preset fast --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264Faster': Tool('x264-faster-arc', 'x264 --preset faster --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264Medium': Tool('x264-medium-arc', 'x264 --preset medium --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264Placebo': Tool('x264-placebo-arc', 'x264 --preset placebo --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264Slow': Tool('x264-slow-arc', 'x264 --preset slow --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264Slower': Tool('x264-slower-arc', 'x264 --preset slower --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264SuperFast': Tool('x264-superfast-arc', 'x264 --preset superfast --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264UltraFast': Tool('x264-ultrafast-arc', 'x264 --preset ultrafast --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264VeryFast': Tool('x264-veryfast-arc', 'x264 --preset veryfast --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),
    'x264VerySlow': Tool('x264-veryslow-arc', 'x264 --preset veryslow --slices 1 --profile high -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames {frames} --input-res {width}x{height} --no-scenecut --tune psnr -o {encoded} {stream}'),

    'x265Fast': Tool('x265-fast-arc', 'x265 --preset fast --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265Faster': Tool('x265-faster-arc', 'x265 --preset faster --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265Medium': Tool('x265-medium-arc', 'x265 --preset medium --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265Placebo': Tool('x265-placebo-arc', 'x265 --preset placebo --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265Slow': Tool('x265-slow-arc', 'x265 --preset slow --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265Slower': Tool('x265-slower-arc', 'x265 --preset slower --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265SuperFast': Tool('x265-superfast-arc', 'x265 --preset superfast --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265UltraFast': Tool('x265-ultrafast-arc', 'x265 --preset ultrafast --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265VeryFast': Tool('x265-veryfast-arc', 'x265 --preset veryfast --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
    'x265VerySlow': Tool('x265-veryslow-arc', 'x265 --preset veryslow --slices 1 -I 120 -i 120 --min-keyint 120 --fps {framerate} --bitrate {bitrate} --vbv-bufsize {2*bitrate} --vbv-maxrate {bitrate} --vbv-init {1.4*bitrate} --frames 999999 --input-res {width}x{height} --high-tier --level-idc 52 -t psnr -o {encoded} {stream}'),
}

def load_csv(src: Path) -> Metrics:
    m = Metrics()
    parts = src.name.split('_')
    m.stream = '_'.join(parts[:-1])

    with src.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            m.codec = row['Codec']

            bitrate = row['Bitrate']
            m.psnr_y[bitrate].append(float(row['PSNR-Y']))
            m.psnr_u[bitrate].append(float(row['PSNR-U']))
            m.psnr_v[bitrate].append(float(row['PSNR-V']))
            m.frame_size[bitrate].append(int(row['Bytes']))

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

        tool = codec2tool[m.codec]
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
    for csv_file in Path('data').glob('*_x265*.csv'):
        print(csv_file.name)
        m = load_csv(csv_file)
        generate_yamls(m)


