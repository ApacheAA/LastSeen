from dataclasses import dataclass
from PIL import Image
from PIL.ImageOps import invert
from sys import platform

from discord.utils import escape_markdown as esc_md
import numpy as np
from scipy.stats import mode
import pytesseract as ts

if platform == 'win32':
    ts.pytesseract.tesseract_cmd = \
    r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TS_KW = {'lang':'eng', 'config':'--psm 7'}

class Box:
    def __init__(self, upper_y, lower_y, left_x, right_x):
        self.uy = upper_y
        self.ly = lower_y
        self.lx = left_x
        self.rx = right_x
        
    def get_global(self, local_uy=0, local_lx=0):
        '''
        Returns
        -------
        uy, ly, lx, rx
        '''
        return (self.uy + local_uy,
                self.ly + local_uy, 
                self.lx + local_lx, 
                self.rx + local_lx)
        
    def check_size(self, min_height=5, min_length=10):
        valid_h = self.ly > self.uy + min_height
        valid_l = self.rx > self.lx + min_length
        return valid_h & valid_l

@dataclass
class Player:
    name: str
    crew_tag: str

def infer_blue_mask(img_arr):
    r_idx, g_idx, b_idx = (np.s_[:, :, i] for i in range(3))
    blue_mask = img_arr[b_idx] - img_arr[g_idx] > 50
    blue_mask &= img_arr[b_idx] > img_arr[g_idx]
    blue_mask &= img_arr[b_idx] - img_arr[r_idx] > 100
    blue_mask &= img_arr[b_idx] > img_arr[r_idx]
    return blue_mask

def infer_white_mask(img_arr):
    white_mask = np.all(img_arr > 225, axis=2)
    #max_c = np.max(img_arr, axis=2)
    #min_c = np.min(img_arr, axis=2)
    #white_mask &= (max_c - min_c) < 10
    return white_mask

def max_length_rectangle(mask):
    '''
    Returns
    -------
    upper_y, lower_y, left_x, right_x : int
    '''
    row_subseries_ids = np.cumsum(~mask, axis=1)
    row_modes, row_counts = mode(row_subseries_ids, axis=1)
    # subseries obtained from cumsum includes exactly one False
    # as first element, so -1 required
    row_counts = row_counts.flatten() - 1
    max_length = row_counts.max()
    
    # for all False mask
    if max_length == 0:
        return (0,) * 4
    
    # all rows with max_length
    row_idxs = np.nonzero(row_counts == max_length)[0]
    upper_y = row_idxs[0]
    lower_y = row_idxs[-1]
    mode_mask = (row_subseries_ids == row_modes)[upper_y]
    # subseries starts with exactly one False, so +1 required
    left_x = np.nonzero(mode_mask)[0][0] + 1
    right_x = left_x + max_length
    return upper_y, lower_y, left_x, right_x        
        
def recon_name_box(img_arr, return_tag=False):
    
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
            crew_tag = img_to_str(tag_img_arr).upper()
    else:
        crew_tag = ''
        
    name = img_to_str(img_arr, invert=True)
    
    if return_tag:
        return Player(name, crew_tag)
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
        '''
        Parameters
        ----------
        img : PIL.Image
        '''

        self.img_arr = np.asarray(img)
        self.h, self.w, self.ch = self.img_arr.shape
        img_arr = self.img_arr[:self.h // 2, self.w // 2:]
        blue_mask = infer_blue_mask(img_arr)
        self.name_box = Box(*max_length_rectangle(blue_mask))
        b = self.name_box
        self.name_box_found = b.check_size()

        if self.name_box_found:
            # certain blue color
            self.blue = mode(img_arr[b.uy, b.lx:b.rx],
                        axis=0
                       ).mode[0]
        
        #TODO test 
        #self.is_valid

#    def find_name_box(self):        
        
#    def find_boxes(self, img):
#        self.KDR_box
#        self.crew_box
    
    def recon_player(self):
        b = self.name_box
        img_arr = self.img_arr[:self.h // 2, self.w // 2:]
        name_img_arr = img_arr[b.uy:b.ly, b.lx:b.rx]
        return recon_name_box(name_img_arr, return_tag=True)
        
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