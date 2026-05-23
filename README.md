# 证件照排版工具

一个面向 Windows 的证件照排版与打印桌面工具。适合照相馆、快照店和个人用户把一张或多张证件照自动排版到 5 寸、6 寸或自定义相纸上，并直接保存或打印。

当前版本：`1.1`

开源地址：[https://github.com/sunchangqing666-ux/photo-layout-tool](https://github.com/sunchangqing666-ux/photo-layout-tool)

## 功能简介

- 支持点击上传和拖拽上传图片
- 支持批量拖入多张照片并批量排版
- 支持一寸、二寸证件照尺寸
- 支持 5 寸、6 寸和自定义相纸尺寸
- 300 DPI 输出，适合照片纸打印
- 支持裁切角线开关，方便后期裁剪
- 支持自动保存开关，批量处理时无需反复确认
- 支持右侧预览，批量照片可用鼠标滚轮切换上一张/下一张
- 支持保存 JPEG，质量 95%，DPI 300
- 支持枚举本机打印机、选择打印机、打开当前打印机属性
- 支持应用内直接打印，Windows 下优先使用 `pywin32` 精确打印
- 支持窗口置顶，方便打印时操作
- 软件内置开源地址入口，方便查看更新

## 支持格式

- JPG / JPEG
- PNG
- BMP
- TIFF / TIF

## 默认尺寸

| 类型 | 名称 | 物理尺寸 | 300 DPI 像素 |
| --- | --- | --- | --- |
| 证件照 | 一寸 | 25 x 35 mm | 295 x 413 px |
| 证件照 | 二寸 | 35 x 49 mm | 413 x 578 px |
| 相纸 | 5 寸 | 89 x 127 mm | 1050 x 1500 px |
| 相纸 | 6 寸 | 4 x 6 inch | 1200 x 1800 px |

## 运行源码

```powershell
python -m pip install -r requirements.txt
python photo_layout_tool.py
```

## 打包 EXE

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

打包完成后，单文件程序位于：

```text
dist\PhotoLayoutTool.exe
```

## 制作安装包

项目提供 Inno Setup 脚本：

```text
PhotoLayoutTool.iss
```

先运行 `build.ps1` 生成 `dist\PhotoLayoutTool.exe`，再使用 Inno Setup 编译 `PhotoLayoutTool.iss`，安装包会输出到 `installer` 目录。

## 开发检查

```powershell
python -m pip install -r requirements-dev.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\test.ps1
```

## 目录说明

```text
photo_layout_tool.py      主程序
assets/                  应用图标与界面 logo
build.ps1                PyInstaller 打包脚本
PhotoLayoutTool.iss      Inno Setup 安装包脚本
requirements.txt         运行依赖
```

## 开源协议

本项目使用 MIT License 开源。
