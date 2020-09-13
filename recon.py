from collections import namedtuple
from PIL import Image
from PIL.ImageOps import invert

import numpy as np
from scipy.stats import mode
import pytesseract as ts

ts.pytesseract.tesseract_cmd = \
r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TS_KW = {'lang':'eng', 'config':'--psm 7'}

class Box:
    def __init__(self, upper_y, lower_y, left_x, right_x):
        self.uy = upper_y
        self.ly = lower_y
        self.lx = left_x
        self.rx = right_x
        
    def to_global(self, local_uy=0, local_lx=0):
        self.uy += local_uy
        self.lx += local_lx

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
        
def recon_name_box(img_arr, return_tag=False):
    player = namedtuple('Player', ('name', 'crew_tag'))
    
    #tag box handling
    white_mask = infer_white_mask(img_arr)
    tag_box = Box(*max_length_rectangle(white_mask))
    tag_box_exists = (tag_box.rx - tag_box.lx) > 25
    if tag_box_exists:
        tag_img_arr = img_arr[tag_box.uy:tag_box.ly,
                              tag_box.lx:tag_box.rx - 2
                             ]
        img_arr = img_arr[:, :tag_box.lx - 4]
        if return_tag:
            crew_tag = img_to_str(tag_img_arr)
    else:
        crew_tag = ''
        
    name = img_to_str(img_arr, invert=True)
    
    if return_tag:
        return player(name, crew_tag)
    else:
        return name        

def img_to_str(img_arr, invert=False):
    if invert:
        arr = 1 - img_arr
    else:
        arr = img_arr
    img_str = ts.image_to_string(arr, **TS_KW)
    img_str = img_str.split('\n')[0]
    return img_str    
    
class ProfileImg:
    
    def __init__(self, img):
        self.img_arr = np.asarray(img)
        self.h, self.w, self.ch = self.img_arr.shape
        img_arr = self.img_arr[:self.h // 2, self.w // 2:]
        blue_mask = infer_blue_mask(img_arr)
        self.name_box = Box(*max_length_rectangle(blue_mask))
        
        # certain blue color
        b = self.name_box
        self.blue = mode(img_arr[b.uy, b.lx:b.rx],
                    axis=0
                   ).mode[0]

#    def find_name_box(self):        
        
#    def find_boxes(self, img):
#        self.KDR_box
#        self.crew_box
    
    def recon_player(self):
        b = self.name_box
        img_arr = self.img_arr[:self.h // 2, self.w // 2:]
        name_img_arr = img_arr[b.uy:b.ly, b.lx:b.rx]
        return recon_name_box(name_img_arr)
        
    def recon_session(self):
        # session players
        sess_players = []
        
        #session list box
        img_arr = self.img_arr[self.name_box.uy:, :self.w // 2]
        blue_mask = (img_arr == self.blue).all(axis=2)
        b_cols = blue_mask.sum(axis=0)
        # most right max blue column
        mrmb_col = np.nonzero(b_cols == b_cols.max())[0][-1]
        # row split
        borders = np.diff(blue_mask[:, mrmb_col].astype(int),
                          prepend=0)
        uys, lys = (np.nonzero(borders == i)[0] for i in [1, -1])
        sess_area_w = self.w // 2 - mrmb_col
        sess_rx = mrmb_col + sess_area_w // 2
        sess_lx = mrmb_col + 2
        
        for uy, ly in  zip(uys, lys):
            name_img_arr = img_arr[uy:ly, sess_lx:sess_rx]
            player = recon_name_box(name_img_arr, return_tag=True)
            sess_players.append(player)
            
        return sess_players        

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