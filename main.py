import os
import time
import json

import cv2
import numpy as np



# File operation
def remove_extension(name):
    name = os.path.splitext(name)[0]
    return name

def add_timestamp_and_png(name):
    timestamp = int(time.time())
    file_name = f'{name}_{timestamp}.png'
    return file_name

def save_image(file_name, image, path, message):
    full_path = os.path.join(path, file_name)
    os.makedirs(path, exist_ok=True)
    cv2.imwrite(full_path, image)
    print(f'{message} {full_path}')



# Extract data
def get_max_feret(contour):
    
    def distance(p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))
    
    def rotate_contour(contour, angle):
        M = cv2.moments(contour)
        if M['m00'] == 0:
            return contour  
        cX = int(M['m10'] / M['m00'])
        cY = int(M['m01'] / M['m00'])
        center = (cX, cY)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_contour = cv2.transform(contour, rotation_matrix)
        return rotated_contour
    
    if len(contour.shape) == 2:
        contour = contour.reshape(-1, 1, 2)
    
    hull = cv2.convexHull(contour, returnPoints=True)
    
    max_distance = 0
    num_angles = 360
    angle_step = 360 / num_angles
    
    for angle in range(0, 360, int(angle_step)):
        rotated_contour = rotate_contour(hull, angle)
        for i in range(len(rotated_contour)):
            for j in range(i + 1, len(rotated_contour)):
                dist = distance(rotated_contour[i][0], rotated_contour[j][0])
                if dist > max_distance:
                    max_distance = dist
    
    return pixel_to_micrometer * max_distance



# Image processing
def cv_show(name, image):
    global resized_image, resize_ratio
    img_height, img_width = image.shape[:2]
    if img_width > screen_width or img_height > screen_height:
        resize_ratio = 0.5
        resized_image = cv2.resize(image, (int(img_width * resize_ratio), int(img_height * resize_ratio)))
    else:
        resize_ratio = 1.0
        resized_image = image
    cv2.imshow(name, resized_image)

def detect_edges(image, binary_threshold_low):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (7, 7), 0)
    _, thresholded_image = cv2.threshold(blurred_image, binary_threshold_low, 255, cv2.THRESH_BINARY)
    canny = cv2.Canny(thresholded_image, 0, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    return cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel)

def setup_trackbar(window_name, initial_threshold_low=200):
    cv2.namedWindow(window_name)
    cv2.createTrackbar('Threshold Low', window_name, initial_threshold_low, 255, lambda x: None)

def get_trackbar_value(window_name):
    threshold_low = cv2.getTrackbarPos('Threshold Low', window_name)
    return threshold_low

def process_with_scrollbar(image, image_filename):
    setup_trackbar(image_filename)
    
    processed_image = image.copy()
    contours = []
    
    cv_show(image_filename, processed_image)
    cv2.moveWindow(image_filename, -1, 1)
    
    prev_threshold_low = get_trackbar_value(image_filename)
    
    while True:
        threshold_low = get_trackbar_value(image_filename)
        
        if threshold_low != prev_threshold_low:
            processed_image = image.copy()
            edges_image = detect_edges(processed_image, threshold_low)
            contours, _ = cv2.findContours(edges_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(processed_image, contours, -1, (0, 0, 255), 1)
            cv_show(image_filename, processed_image)
            cv2.moveWindow(image_filename, 1, 1)
            
            prev_threshold_low = threshold_low
            
        cv2.setMouseCallback(image_filename, mouse_callback, (contours, processed_image, image_filename))
        
        key = cv2.waitKey(100) & 0xFF  
        if key == ord('q'):  
            break

    cv2.destroyAllWindows()

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        original_x = int(x / resize_ratio)
        original_y = int(y / resize_ratio)
        print(f"Mouse clicked at: ({original_x}, {original_y})")



# Load user configuration from config.json
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

screen_width = config['screen_width']
screen_height = config['screen_height']

accepted_extensions = config['accepted_extensions_for_images']
unprocessed_images_directory = config['unprocessed_images_directory']

detected_particles_directory = config['detected_particles_directory']
excel_file = config['excel_file']

scale_bar_width_pixels = config['scale_bar_width_pixels']
scale_bar_value_micrometers = config['scale_bar_value_micrometers']
pixel_to_micrometer = scale_bar_value_micrometers / scale_bar_width_pixels

min_feret_bool = config['min_feret_diameter']
max_feret_bool = config['max_feret_diameter']
roundness_bool = config['roundness']





# Detect images and process them one by one
unprocessed_image_files = [
    file for file in os.listdir(unprocessed_images_directory)
    if os.path.isfile(os.path.join(unprocessed_images_directory, file))
    and os.path.splitext(file)[1].lower() in accepted_extensions  
]
print(f'Detected: {len(unprocessed_image_files)} images')

if not unprocessed_image_files:
    print("No unprocessed images found")
    exit()
    
for image_filename in unprocessed_image_files:
    path = os.path.join(unprocessed_images_directory, image_filename)
    print("Displaying image:", path)
    image = cv2.imread(path)
    
    process_with_scrollbar(image, image_filename)
    
    cv2.waitKey()
    cv2.destroyAllWindows()