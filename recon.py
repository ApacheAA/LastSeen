from io import BytesIO
from PIL import Image
from PIL.ImageOps import invert

import numpy as np
from scipy.stats import mode
import pytesseract

pytesseract.pytesseract.tesseract_cmd = \
r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def infer_blue_mask(img_arr):
    r_idx, g_idx, b_idx = (np.s_[:, :, i] for i in range(3))
    blue_mask = img_arr[b_idx] - img_arr[g_idx] > 50
    blue_mask &= img_arr[b_idx] > img_arr[g_idx]
    blue_mask &= img_arr[b_idx] - img_arr[r_idx] > 100
    blue_mask &= img_arr[b_idx] > img_arr[r_idx]
    return blue_mask

def infer_white_mask(img_arr):
    white_mask = np.all(img_arr > 225, axis=2)
    max_c = np.max(img_arr, axis=2)
    min_c = np.min(img_arr, axis=2)
    white_mask &= (max_c - min_c) < 10
    return white_mask

def max_length_rectangle(mask):
    rows_m = mode(np.cumsum(~mask, axis=1), axis=1)
    max_length = rows_m.count.max()
    row_idxs = np.nonzero(rows_m.count.flatten() == max_length)[0]
    upper_y = row_idxs[0]
    lower_y = row_idxs[-1]
    left_x = rows_m.mode.flatten()[upper_y]
    right_x = left_x + max_length
    return upper_y, lower_y, left_x, right_x

def get_name(img):
    img_arr = np.asarray(img)
    h, w, ch = img_arr.shape
    img_arr = img_arr[:h // 2, w // 2:]
    
    blue_mask = infer_blue_mask(img_arr)
    uy, ly, lx, rx = max_length_rectangle(blue_mask)
    
    # TODO certain blue color
    
    img_arr = img_arr[uy:ly, lx:rx]
    white_mask = infer_white_mask(img_arr)
    uy, ly, lx, rx = max_length_rectangle(white_mask)
    name_img = Image.fromarray(img_arr[:, :lx])
    name_img = invert(name_img).convert('L')
    name = pytesseract.image_to_string(name_img,
                                       lang='eng',
                                       config='--psm 7')
    name = name.split('\n')[0]
    # TODO no name found
    return name