#!/usr/bin/env python3
import ezdxf
import numpy as np
from PIL import Image
import yaml
import argparse
import os

def cad_to_map(dxf_path, output_pgm, output_yaml, resolution=0.05, origin=(0.0, 0.0)):
    """
    将 DXF 文件转换为 ROS 栅格地图
    :param dxf_path: DXF 文件路径
    :param output_pgm: 输出图片路径 (.pgm)
    :param output_yaml: 输出描述文件路径 (.yaml)
    :param resolution: 地图分辨率 (m/pixel)
    :param origin: 地图原点 (x, y)
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # 提取所有线条和多段线（作为障碍物轮廓）
    lines = []
    for entity in msp:
        if entity.dxftype() == 'LINE':
            lines.append((entity.dxf.start, entity.dxf.end))
        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.vertices())
            for i in range(len(points)-1):
                lines.append((points[i], points[i+1]))

    if not lines:
        print("No lines found in DXF")
        return

    # 计算地图边界
    all_points = []
    for start, end in lines:
        all_points.append(start)
        all_points.append(end)
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # 添加边距
    margin = 1.0  # 米
    min_x -= margin
    max_x += margin
    min_y -= margin
    max_y += margin

    # 计算图像尺寸
    width = int((max_x - min_x) / resolution)
    height = int((max_y - min_y) / resolution)

    # 创建空白图像 (白色: 自由, 黑色: 障碍物)
    img = Image.new('L', (width, height), 255)  # 255 白色
    pixels = img.load()

    # 将线条绘制到图像上
    for start, end in lines:
        # 将世界坐标转换为像素坐标
        x1 = int((start[0] - min_x) / resolution)
        y1 = height - int((start[1] - min_y) / resolution)  # 图像 y 轴向下
        x2 = int((end[0] - min_x) / resolution)
        y2 = height - int((end[1] - min_y) / resolution)

        # 使用 Bresenham 算法画线
        draw_line(pixels, x1, y1, x2, y2, 0)  # 黑色

    # 保存图片
    img.save(output_pgm)

    # 生成 YAML 文件
    map_yaml = {
        'image': os.path.basename(output_pgm),
        'resolution': resolution,
        'origin': [min_x + origin[0], min_y + origin[1], 0.0],
        'occupied_thresh': 0.65,
        'free_thresh': 0.25,
        'negate': 0
    }
    with open(output_yaml, 'w') as f:
        yaml.dump(map_yaml, f, default_flow_style=False)

def draw_line(pixels, x0, y0, x1, y1, color):
    """Bresenham 直线算法"""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < pixels.im.size[0] and 0 <= y0 < pixels.im.size[1]:
            pixels[x0, y0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert DXF to ROS map')
    parser.add_argument('dxf', help='Input DXF file')
    parser.add_argument('--output_dir', default='.', help='Output directory')
    parser.add_argument('--resolution', type=float, default=0.05, help='Map resolution (m/pixel)')
    parser.add_argument('--origin_x', type=float, default=0.0, help='Origin X offset')
    parser.add_argument('--origin_y', type=float, default=0.0, help='Origin Y offset')
    args = parser.parse_args()

    base = os.path.splitext(os.path.basename(args.dxf))[0]
    pgm_path = os.path.join(args.output_dir, base + '.pgm')
    yaml_path = os.path.join(args.output_dir, base + '.yaml')

    cad_to_map(args.dxf, pgm_path, yaml_path, args.resolution, (args.origin_x, args.origin_y))
    print(f"Generated {pgm_path} and {yaml_path}")