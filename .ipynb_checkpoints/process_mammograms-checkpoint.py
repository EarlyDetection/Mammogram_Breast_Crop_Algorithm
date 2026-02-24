import pydicom
import cv2
import numpy as np
import argparse
from pathlib import Path

def get_breast_contour(dcm_array):
    binary_img = cv2.threshold(dcm_array, 5, 255, cv2.THRESH_BINARY)[1].astype(np.uint8)
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)

def process_file(input_path, output_dir, do_crop, do_clean):
    try:
        ds = pydicom.dcmread(input_path)
        dcm = ds.pixel_array.copy()
        
        largest_contour = get_breast_contour(dcm)
        if largest_contour is None:
            print(f"Skipping {input_path.name}: No breast contour found.")
            return

        if do_clean:
            mask = np.zeros(dcm.shape, dtype=np.uint8)
            cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
            dcm = np.where(mask == 255, dcm, 0)
            suffix = "_cleaned"

        if do_crop:
            x, y, w, h = cv2.boundingRect(largest_contour)
            dcm = dcm[y:y+h, x:x+w]
            suffix = "_cropped"

        ds.PixelData = dcm.tobytes()
        ds.Rows, ds.Columns = dcm.shape
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        
        out_name = f"{input_path.stem}{suffix}.dcm"
        save_path = output_dir / out_name
        ds.save_as(save_path)
        print(f"Successfully saved: {out_name}")

    except Exception as e:
        print(f"Error processing {input_path.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Mammogram Preprocessing Tool")
    parser.add_argument("input", help="Path to a DICOM file or a directory of DICOMs")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-crop", action="store_true", help="Perform tight crop around breast")
    group.add_argument("-clean_background", action="store_true", help="Remove text/noise from background")
    
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path("Processed_Mammograms")
    output_dir.mkdir(exist_ok=True)

    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = list(input_path.glob("*.dcm"))
    else:
        print(f"Error: {args.input} is not a valid file or directory.")
        return

    if not files:
        print("No DICOM files found to process.")
        return

    for f in files:
        process_file(f, output_dir, args.crop, args.clean_background)

if __name__ == "__main__":
    main()