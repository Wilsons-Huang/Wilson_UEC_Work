from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET


VOID_REASON = "註銷重開"
NAMESPACE = "urn:GEINV:eInvoiceMessage:F0701:4.1"


def get_system_date_compact() -> str:
    return datetime.now().strftime("%Y%m%d")


def get_system_time_hhmmss() -> str:
    return datetime.now().strftime("%H%M%S")


def convert_time(raw_time: str) -> str:
    return f"{raw_time[0:2]}:{raw_time[2:4]}:{raw_time[4:6]}"


def get_system_datetime_compact2() -> str:
    # Match Java DateUtility.PATTERN_DATETIME_COMPACT2 style: yyyyMMddHHmmssSSS
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"


def product_file(
    inv_number: str,
    inv_date: str,
    buyer_id: str,
    seller_id: str,
    output_dir: Path,
    void_reason: str,
) -> None:
    ET.register_namespace("", NAMESPACE)
    root = ET.Element(f"{{{NAMESPACE}}}VoidInvoice")
    ET.SubElement(root, f"{{{NAMESPACE}}}VoidInvoiceNumber").text = inv_number
    ET.SubElement(root, f"{{{NAMESPACE}}}InvoiceDate").text = inv_date.replace("/", "")
    ET.SubElement(root, f"{{{NAMESPACE}}}BuyerId").text = buyer_id
    ET.SubElement(root, f"{{{NAMESPACE}}}SellerId").text = seller_id
    ET.SubElement(root, f"{{{NAMESPACE}}}VoidDate").text = get_system_date_compact()
    ET.SubElement(root, f"{{{NAMESPACE}}}VoidTime").text = convert_time(get_system_time_hhmmss())
    ET.SubElement(root, f"{{{NAMESPACE}}}VoidReason").text = void_reason

    file_name = f"F0701_{seller_id}_{inv_number}_{get_system_datetime_compact2()}.xml"
    file_path = output_dir / file_name
    tree = ET.ElementTree(root)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)
    print(f"{file_path.resolve()} 產檔完畢")


def from_file(input_dir: Path, output_dir: Path, void_reason: str) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    for text_file in sorted(input_dir.iterdir()):
        if not text_file.is_file():
            continue
        if text_file.suffix.lower() not in {".txt", ".csv"}:
            continue

        print(f"{text_file.name} -- 開始")
        with text_file.open("r", encoding="utf-8") as bf:
            for line in bf:
                buffer = line.strip()
                if not buffer:
                    continue

                data = [item.strip() for item in buffer.split(",")]
                if len(data) < 4:
                    raise ValueError(f"資料格式錯誤，需為4欄: {buffer}")

                inv_number = data[0]
                inv_date = data[1].replace("-", "")
                buyer_id = data[2]
                seller_id = data[3]
                product_file(inv_number, inv_date, buyer_id, seller_id, output_dir, void_reason)

        print(f"{text_file.name} -- 結束")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_output_dir = Path(r"D:\D\wilsonhuang\EINV發票問題檔案\註銷訊息F0701")
    parser = argparse.ArgumentParser(description="Generate F0701 void invoice XML files from txt/csv lines.")
    parser.add_argument("--input-dir", default=str(script_dir), help="Input directory containing text files.")
    parser.add_argument("--output-dir", default=str(default_output_dir), help="Output directory for generated XML files.")
    parser.add_argument("--void-reason", default=VOID_REASON, help="Value for <VoidReason> in generated XML.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from_file(Path(args.input_dir), Path(args.output_dir), args.void_reason)


if __name__ == "__main__":
    main()
