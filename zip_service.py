import os
import pyzipper as zipfile
from pathlib import Path
from typing import List, Optional


def _create_zipinfo(filename: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=filename)
    info.flag_bits |= 0x800
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _decode_filename(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode('cp437').decode('gbk')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def zip_directory(source_dir: str, output_path: str, include_hidden: bool = False, password: Optional[str] = None) -> str:
    source_path = Path(source_dir).resolve()
    if not source_path.is_dir():
        raise ValueError(f"源路径不是一个目录: {source_dir}")

    output = Path(output_path).resolve()
    if output.suffix.lower() != '.zip':
        output = output.with_suffix('.zip')

    output.parent.mkdir(parents=True, exist_ok=True)

    pwd = password.encode('utf-8') if password else None
    compression = zipfile.ZIP_DEFLATED
    encryption = zipfile.WZ_AES if password else None

    with zipfile.ZipFile(output, 'w', compression=compression, encryption=encryption) as zipf:
        if pwd:
            zipf.setpassword(pwd)
        for root, dirs, files in os.walk(source_path):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                files = [f for f in files if not f.startswith('.')]

            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_path)
                with open(file_path, 'rb') as f:
                    data = f.read()
                info = _create_zipinfo(str(arcname))
                info.file_size = len(data)
                zipf.writestr(info, data)

    return str(output)


def zip_files(file_paths: List[str], output_path: str, base_dir: Optional[str] = None, password: Optional[str] = None) -> str:
    if not file_paths:
        raise ValueError("文件路径列表不能为空")

    output = Path(output_path).resolve()
    if output.suffix.lower() != '.zip':
        output = output.with_suffix('.zip')

    output.parent.mkdir(parents=True, exist_ok=True)

    base_path = Path(base_dir).resolve() if base_dir else None

    pwd = password.encode('utf-8') if password else None
    compression = zipfile.ZIP_DEFLATED
    encryption = zipfile.WZ_AES if password else None

    with zipfile.ZipFile(output, 'w', compression=compression, encryption=encryption) as zipf:
        if pwd:
            zipf.setpassword(pwd)
        for file_path in file_paths:
            path = Path(file_path).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            if base_path:
                try:
                    arcname = path.relative_to(base_path)
                except ValueError:
                    arcname = path.name
            else:
                arcname = path.name

            with open(path, 'rb') as f:
                data = f.read()
            info = _create_zipinfo(str(arcname))
            info.file_size = len(data)
            zipf.writestr(info, data)

    return str(output)


def unzip_file(zip_path: str, extract_dir: str, password: Optional[str] = None) -> str:
    zip_file = Path(zip_path).resolve()
    if not zip_file.is_file():
        raise FileNotFoundError(f"ZIP 文件不存在: {zip_path}")

    if zip_file.suffix.lower() != '.zip':
        raise ValueError(f"不是 ZIP 文件: {zip_path}")

    extract_path = Path(extract_dir).resolve()
    extract_path.mkdir(parents=True, exist_ok=True)

    pwd = password.encode('utf-8') if password else None

    with zipfile.ZipFile(zip_file, 'r') as zipf:
        if pwd:
            zipf.setpassword(pwd)
        for info in zipf.infolist():
            filename = _decode_filename(info)
            if info.is_dir():
                (extract_path / filename).mkdir(parents=True, exist_ok=True)
            else:
                target_path = extract_path / filename
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zipf.open(info, pwd=pwd) as source, open(target_path, 'wb') as target:
                    target.write(source.read())

    return str(extract_path)


def list_zip_contents(zip_path: str, password: Optional[str] = None) -> List[dict]:
    zip_file = Path(zip_path).resolve()
    if not zip_file.is_file():
        raise FileNotFoundError(f"ZIP 文件不存在: {zip_path}")

    if zip_file.suffix.lower() != '.zip':
        raise ValueError(f"不是 ZIP 文件: {zip_path}")

    pwd = password.encode('utf-8') if password else None

    contents = []
    with zipfile.ZipFile(zip_file, 'r') as zipf:
        if pwd:
            zipf.setpassword(pwd)
        for info in zipf.infolist():
            contents.append({
                'name': _decode_filename(info),
                'size': info.file_size,
                'compressed_size': info.compress_size,
                'is_dir': info.is_dir(),
                'compress_type': info.compress_type,
            })

    return contents


def is_zip_file(file_path: str) -> bool:
    path = Path(file_path)
    if not path.is_file():
        return False
    return zipfile.is_zipfile(str(path))


def main():
    import argparse

    parser = argparse.ArgumentParser(description='ZIP 压缩解压服务')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    zip_parser = subparsers.add_parser('zip', help='压缩文件夹')
    zip_parser.add_argument('source', help='源文件夹路径')
    zip_parser.add_argument('output', help='输出 ZIP 文件路径')
    zip_parser.add_argument('--include-hidden', action='store_true', help='包含隐藏文件')
    zip_parser.add_argument('--password', help='ZIP 文件加密密码（AES 加密）')

    unzip_parser = subparsers.add_parser('unzip', help='解压 ZIP 文件')
    unzip_parser.add_argument('zip_file', help='ZIP 文件路径')
    unzip_parser.add_argument('extract_dir', help='解压目标目录')
    unzip_parser.add_argument('--password', help='ZIP 文件密码')

    list_parser = subparsers.add_parser('list', help='列出 ZIP 文件内容')
    list_parser.add_argument('zip_file', help='ZIP 文件路径')
    list_parser.add_argument('--password', help='ZIP 文件密码')

    check_parser = subparsers.add_parser('check', help='检查是否为 ZIP 文件')
    check_parser.add_argument('file', help='文件路径')

    args = parser.parse_args()

    if args.command == 'zip':
        try:
            result = zip_directory(args.source, args.output, args.include_hidden, args.password)
            if args.password:
                print(f"压缩成功（已加密）: {result}")
            else:
                print(f"压缩成功: {result}")
        except Exception as e:
            print(f"压缩失败: {e}")
            exit(1)

    elif args.command == 'unzip':
        try:
            result = unzip_file(args.zip_file, args.extract_dir, args.password)
            print(f"解压成功: {result}")
        except Exception as e:
            print(f"解压失败: {e}")
            exit(1)

    elif args.command == 'list':
        try:
            contents = list_zip_contents(args.zip_file, args.password)
            print(f"ZIP 文件内容 ({len(contents)} 项):")
            for item in contents:
                type_str = '目录' if item['is_dir'] else '文件'
                print(f"  {item['name']} ({type_str}, 原始: {item['size']} 字节, 压缩后: {item['compressed_size']} 字节)")
        except Exception as e:
            print(f"读取失败: {e}")
            exit(1)

    elif args.command == 'check':
        result = is_zip_file(args.file)
        print(f"是 ZIP 文件: {result}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
