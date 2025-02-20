# -*- coding: utf-8 -*-
"""fill_testing.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1IpGB9grnZAsrrLNaQlmJVwimAI9YGqGJ

# **Imports and Function Definitions**
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
from PIL import Image
import cv2
import matplotlib.pyplot as plt
from scipy.interpolate import splprep, splev, CubicSpline
from sklearn.cluster import KMeans
import random
from matplotlib.animation import FuncAnimation
import matplotlib.animation as animation
import matplotlib.transforms as transforms
from rdp import rdp
import copy
import sys
import os
from matplotlib.widgets import Button
from matplotlib.image import imread
# %matplotlib notebook
sys.setrecursionlimit(10000)
from google.colab import drive
# %matplotlib inline
drive.mount('/content/drive/')

# Input: Image path
# Output: RGB Image of shape (h, w, 3)

def s0_prepare_img(img_path, border_size = 2, display = False):
    img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Obtain image background color (assumed top-left pixel)
    background_color = img_rgb[0, 0].tolist()

    # Add a  border around the image
    img_with_border = cv2.copyMakeBorder(
        img_rgb,
        top = border_size,
        bottom = border_size,
        left = border_size,
        right = border_size,
        borderType = cv2.BORDER_CONSTANT,
        value = background_color)

    if display:
        plt.imshow(img_with_border)
        plt.axis('off')
        plt.show()

    return img_with_border

# Input: RGB image of shape (h, w, 3)
# Output: RGB image of shape (h, w, 3)

def s1_reduce_img_rgbs(img_rgb, k = 4, display = False):
    # Reshape input image for RGB processing
    img_height, img_width, _ = img_rgb.shape
    pixels = img_rgb.reshape(img_height * img_width, 3)

    # Obtain center RGB values of k clusters using k-means
    kmeans = KMeans(n_clusters = k, random_state = 0)
    kmeans.fit(pixels)
    selected_rgbs = np.round(kmeans.cluster_centers_).astype(int)

    # Initialize output image
    img_reduced_rgb = np.zeros_like(img_rgb)

    # Iterate through all image pixels and assign new output image pixel RGBs as the most similar K-means center
    for y in range(img_height):
        for x in range(img_width):
            rgb_errors = np.zeros((k))
            pixel_rgb = img_rgb[y, x, :]
            # Compute the error between the image pixel RGB and each k-means cluster center
            for i in range((k)):
                rgb_errors[i] = np.sqrt(np.mean((selected_rgbs[i] - pixel_rgb) ** 2))
            # Select RGB with lowest error and assign to the correpsonding output image pixel
            rgb_index = np.argmin(rgb_errors)
            img_reduced_rgb[y, x] = selected_rgbs[rgb_index]

    if display == True:
        plt.imshow([selected_rgbs])
        plt.show()
        plt.imshow(img_reduced_rgb)
        plt.show()

    return img_reduced_rgb

# Input: RGB image
# Output: Binary image of shape (h, w, 1)

def s2_generate_edges(img_rgb, display = False):
    # Initialize output edges image
    img_height, img_width, _ = img_rgb.shape
    img_edges = np.zeros_like(img_rgb[:, :, 0])

    # Establish pixel range for 'neighbor' processing
    y_range = [0, 1]
    x_range = [0, 1]

    # Iterate over all image pixels
    for y in range(img_height):
        for x in range(img_width):
            # Initialize a set to track all discovered RGBs among itself and its neighbors
            tracked_rgbs = set()
            # Iterate over relevant pixels (itself and its neighbors)
            for y_offset in y_range:
                for x_offset in x_range:
                    y_neighbor, x_neighbor = y + y_offset, x + x_offset
                    # Ensure pixel is within image dimesnion range
                    if 0 <= y_neighbor < img_height and 0 <= x_neighbor < img_width:
                        # Add discovered RGB to the tracked_rgbs set
                        neighbor_rgb = tuple(img_rgb[y_neighbor, x_neighbor])
                        tracked_rgbs.add(neighbor_rgb)
            # If more than one RGB is discovered within the pixel's range, set pixel as an edge
            if len(tracked_rgbs) > 1:
                img_edges[y, x] = 255

    if display == True:
        plt.imshow(img_edges)
        plt.show()

    return img_edges

# Input: Binary image
# Output: List of arrays of tuples (List length: number of edges; array length: number of pixels in given edge; tuples: pixel y and x coordinates)
def s3_group_edges(img_edges, edge_threshold = 50):
    # Initialize list of edges
    edges = []
    # Obtain connected compoennts
    num_labels, img_labels = cv2.connectedComponents(img_edges)
    for label in range(1, num_labels):
        edge_points = np.argwhere(img_labels == label)
        # Condition on minimum edge length
        if len(edge_points) >= edge_threshold:
            # Format and add edges to the output list
            edge_points_set = {tuple(point) for point in edge_points}
            edges.append(np.array(list(edge_points_set)))
    return edges

# Helper function: Identify the closest pixel to a given current pixel
def closest_point(curr, points):
    if len(points) == 0:
        raise ValueError('Invalid number of remaining points')
    min_dist = float('inf')
    min_point = None
    # Iterate through all remaining pixels
    for i, point in enumerate(points):
        # Calculate the distance between the current point and the remaining pixels
        dist = np.linalg.norm(np.array(curr) - np.array(point))
        # Update pixel if it has the shortest distance among traversed pixels
        if dist < min_dist:
            min_dist = dist
            min_point = point
    return min_dist, min_point

def helper(curr, remaining, all_sections, ordered_section, mode, dist_thresh,
           section_size_thresh):
    # Return if there are no longer any remaining pixels
    if len(remaining) == 0:
        all_sections.append(ordered_section)
        return

    # Obtain the closest remaining pixel to the current pixel
    min_dist, min_point = closest_point(curr, remaining)
    # The closest pixel is within the predetermined distance threhold
    if min_dist < dist_thresh:
        # Add pixel to end of ordered section when in forward mode
        if mode == 'forward':
            ordered_section.append(min_point)
        # Add pixel to start of ordered section when in backward mode
        else:
            ordered_section.insert(0, min_point)
        # Update remaining pixels and current pixel
        remaining.remove(min_point)
        curr = min_point
        # Call the function again
        helper(curr, remaining, all_sections, ordered_section, mode, dist_thresh,
               section_size_thresh)
    # The closest pixel is beyond the predetermined distance threshold
    else:
        # If in forward mode, update to backward mode, update current pixel and call the function again
        if mode == 'forward':
            mode = 'backward'
            curr = ordered_section[0]
            helper(curr, remaining, all_sections, ordered_section, mode, dist_thresh,
                   section_size_thresh)
        # If in backward mode and section is above minimum length, it is appended to the sections list and a new current pixel is identified
        elif mode == 'backward':
            if len(ordered_section) > section_size_thresh:
              all_sections.append(ordered_section)
            ordered_section = []
            curr = remaining.pop()
            ordered_section.append(curr)
            mode = 'forward'
            helper(curr, remaining, all_sections, ordered_section, mode, dist_thresh,
                   section_size_thresh)

# Input: List of arrays of tuples, int, int
# Output: List of arrays of tuples (List length: number of edges; array length: number of pixels in given edge; tuples: pixel y and x coordinates)
def s4_order_edges(edges, dist_thresh, section_size_thresh):
    ordered_edges = []
    for edge in edges:
        edge = list(map(tuple, edge))
        ordered_edge = []
        ordered_section = []
        remaining = set(edge)
        curr = remaining.pop()
        ordered_section.append(curr)
        mode = 'forward'
        all_sections = []

        helper(curr, remaining, all_sections, ordered_section, mode, dist_thresh,
               section_size_thresh)

        ordered_edges.append(all_sections)

    return ordered_edges

# List of arrays of tuples, int
# Output: List of arrays of tuples (List length: number of edges; array length: number of pixels in given edge; tuples: pixel y and x coordinates)
def s5_simplify_path(ordered_edges, epsilon):
    simplified_paths = []
    for edge in ordered_edges:
        edge = edge[0]
        simplified_edge = rdp(edge, epsilon=epsilon)
        simplified_paths.append(simplified_edge)
    return simplified_paths

# Input: List of arrays of tuples, string (output file path)
def s6_generate_output(paths, output_file):
  for i in range(len(simplified_paths)):
    if simplified_paths[i][-1] != simplified_paths[i][0]:
      simplified_paths[i].append(simplified_paths[i][0])
  painting_toggle = 1
  all_waypoints = []
  for i, path in enumerate(simplified_paths):
    for j, coord in enumerate(path):
      x, y = coord
      if j == len(path) - 1:
        painting_toggle = 1
      all_waypoints.append((x, y, painting_toggle))
      painting_toggle = 0
    painting_toggle = 1

  with open(output_file, "w") as file:
    for waypoint in all_waypoints:
      file.write(f"{waypoint[0]}, {waypoint[1]}, {waypoint[2]}\n")

  print('Generated Waypoints at ', output_file)

def s7_animate_output(paths, animation_output_filename):
  # First and second sets of corners
  corners1 = copy.deepcopy(paths[0])  # Replace with your first set
  corners2 = copy.deepcopy(paths[1])  # Replace with your second set

  # Function to generate equidistant points along the trajectory
  def generate_equidistant_points(points, num_points=100):
      # Compute distances between consecutive points
      distances = np.sqrt(np.sum(np.diff(points, axis=0) ** 2, axis=1))
      cumulative_distances = np.insert(np.cumsum(distances), 0, 0)  # Start with 0 distance

      # Create target distances ensuring all original points are included
      total_distance = cumulative_distances[-1]
      target_distances = np.linspace(0, total_distance, num=num_points)
      target_distances = np.unique(np.concatenate([target_distances, cumulative_distances]))
      target_distances.sort()  # Sort in ascending order

      # Interpolate x and y coordinates
      x = np.interp(target_distances, cumulative_distances, points[:, 0])
      y = np.interp(target_distances, cumulative_distances, points[:, 1])

      return np.column_stack((x, y))

  # Generate equidistant points for the two trajectories and transition
  pixels1 = generate_equidistant_points(corners1, num_points=200)
  pixels2 = generate_equidistant_points(corners2, num_points=200)
  transition = generate_equidistant_points(np.array([corners1[-1], corners2[0]]), num_points=10)

  # Combine all points
  pixels = np.vstack((pixels1, transition, pixels2))
  pixels = np.column_stack((pixels[:, 1], -pixels[:, 0])) # rotate to fix


  # Define frame ranges for each phase
  phase1_frames = len(pixels1)
  transition_frames = len(transition)
  phase2_frames = len(pixels2)

  # Load the robot PNG image
  robot_image = imread("/content/drive/Shareddrives/Senior Design :D/Code/hue_robot.jpeg")  # Replace with the path to your robot PNG

  # Set up the figure and axis
  fig, ax = plt.subplots(figsize=(10, 10))
  ax.set_xlim(np.min(pixels[:, 0]) - 25, np.max(pixels[:, 0]) + 25)
  ax.set_ylim(np.min(pixels[:, 1]) - 25, np.max(pixels[:, 1]) + 25)
  ax.set_title("Simulation of Hue Robot Painting Trajectory", fontsize=18)

  # Initialize line objects for each phase
  unpainted_line, = ax.plot(pixels[:, 0], pixels[:, 1], color='gray', lw=3, alpha=0.5, label="Planned Path")
  painted_phase1, = ax.plot([], [], c='blue', lw=3, label="Painted Path")
  painted_transition, = ax.plot([], [], c='red', lw=3, label="Unpainted Transition Path")
  painted_phase2, = ax.plot([], [], c='blue', lw=3)
  ax.set_xticks([])
  ax.set_xticks([], minor=True)
  ax.set_xticklabels([])
  ax.set_yticks([])
  ax.set_yticks([], minor=True)
  ax.set_yticklabels([])
  ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.02),
            fancybox=True, shadow=True, ncol=5, fontsize=15)

  # Create an imshow object for the robot image
  robot = ax.imshow(robot_image, extent=[0, 1, 0, 1])  # Placeholder extent; will be updated

  # Initialization function: plot background of each frame
  def init():
      painted_phase1.set_data([], [])
      painted_transition.set_data([], [])
      painted_phase2.set_data([], [])
      unpainted_line.set_data(pixels[:, 0], pixels[:, 1])  # Full unpainted line
      robot.set_extent([0, 1, 0, 1])  # Initialize robot position
      return painted_phase1, painted_transition, painted_phase2, unpainted_line, robot

  # Animation function: update robot position and painted line
  def animate(i):
      if i < phase1_frames:
          # First phase
          painted_phase1.set_data(pixels[:i + 1, 0], pixels[:i + 1, 1])
      elif i < phase1_frames + transition_frames:
          # Transition phase
          transition_start = phase1_frames
          painted_transition.set_data(pixels[transition_start:i + 1, 0], pixels[transition_start:i + 1, 1])
      else:
          # Second phase
          phase2_start = phase1_frames + transition_frames
          painted_phase2.set_data(pixels[phase2_start:i + 1, 0], pixels[phase2_start:i + 1, 1])

      # Update unpainted line
      unpainted_line.set_data(pixels[i:, 0], pixels[i:, 1])

      # Update robot position
      x, y = pixels[i]
      robot_size = 20  # Adjust the size of the robot image
      robot.set_extent([x - robot_size, x + robot_size, y - robot_size, y + robot_size])
      return painted_phase1, painted_transition, painted_phase2, unpainted_line, robot

  '''
  # Add a "Stop" button
  def stop(event):
      ani.event_source.stop()

  def play(event):
      ani.event_source.start()

  play_button_ax = fig.add_axes([0.65, 0.025, 0.1, 0.04])  # Position for the button
  play_button = Button(play_button_ax, 'Play')
  play_button.on_clicked(play)

  stop_button_ax = fig.add_axes([0.8, 0.025, 0.1, 0.04])  # Position for the button
  stop_button = Button(stop_button_ax, 'Stop')
  stop_button.on_clicked(stop)
  '''

  def on_key_press(event):
      if event.key == 'q':
          ani.event_source.stop()  # Stop the animation
          plt.close()  # Close the figure
  fig.canvas.mpl_connect('key_press_event', on_key_press)
  # Call the animator
  ani = FuncAnimation(fig, animate, init_func=init, frames=len(pixels), interval=50, blit=True)

  # Save the animation as a GIF
  ani.save('animation_final.gif', writer='pillow', fps=60, dpi=150)

  # Show the animation
  plt.show()

"""# **Initialize Image Path and Other Variables**"""

uploaded_image_path = '/content/drive/Shareddrives/Senior Design :D/Image Processing/Media/penn_logo_sharp.png'
k = 3
border_size = 2
min_points_per_edge = 50
max_dist_betw_points = 5
min_section_size = 10
waypoints_output_filename = 'image_waypoints.txt'
animation_output_filename = 'image_animation.gif'

"""# **Step 0: Read In and Preprocess Image**
###### **s0_prepare_img**

###### The s0_prepare_img function reads the uploaded .jpg, .png or other compatible file as an RGB image with shape (height, width, 3), where 3 represents the red, green and blue color channels. The A border of width 'border_size = 2' is added to the image, and is returned by the function.
"""

img_rgb = s0_prepare_img(uploaded_image_path, border_size=border_size, display=True)

"""# **Step 1: Reduce RGBs To Main Colors**

###### **s1_reduce_img_rgbs**

###### The s1_reduce_img_rgbs function takes an RGB image as input and uses k-means clustering to establish k RGB clusters within which each pixel belongs. The centers of these clusters, which can be interpreted as the average colors, are deemed as 'selected' rgbs. For each pixel within the image, the closest center to the given pixel's original color is assigned in its place. This ultimately yields a full RGB image reduced to only k colors.
"""

img_reduced_rgb = s1_reduce_img_rgbs(img_rgb, k=k, display=True)

pre_reduction_unique = len(set(list(map(tuple, img_rgb.reshape(-1, 3)))))
post_reduction_unique = len(set(list(map(tuple, img_reduced_rgb.reshape(-1, 3)))))
print('Number of Unique RGB Triples (Colors) Before Reduction: ', pre_reduction_unique)
print('Number of Unique RGB Triples (Colors) After Reduction: ', post_reduction_unique)
print('Reduction %: ', round((1 - (post_reduction_unique / pre_reduction_unique)) * 100, 4))

plt.imshow(img_reduced_rgb)

!pip install --upgrade scikit-image scipy

import numpy as np
import cv2
import matplotlib.pyplot as plt
from skimage import measure, color
from scipy.ndimage import binary_fill_holes

def generate_fill_waypoints(image_rgb, threshold=127, step=10):
    """
    Generates waypoints for a robot to fill connected components in an RGB image.

    Parameters:
    - image_rgb: NumPy array of shape (H, W, 3), the input RGB image.
    - threshold: Intensity threshold for binarization.
    - step: Vertical step size for the boustrophedon pattern.

    Returns:
    - waypoints: List of (x, y) tuples representing the robot's path.
    - labeled_image: NumPy array with labeled connected components.
    """
    # Convert RGB to Grayscale
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    # Binarize the image
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

    # Optional: Fill holes within the connected components
    binary_filled = binary_fill_holes(binary // 255)

    # Label connected components
    labeled_image = measure.label(binary_filled, connectivity=2)
    num_labels = labeled_image.max()
    print(f"Number of connected components: {num_labels}")

    waypoints = []

    for label in range(1, num_labels + 1):
        # Create mask for the current component
        component_mask = (labeled_image == label).astype(np.uint8)

        # Find bounding box
        props = measure.regionprops(component_mask)
        if not props:
            continue
        props = props[0]
        min_row, min_col, max_row, max_col = props.bbox

        # Generate waypoints using boustrophedon pattern
        for y in range(min_row, max_row, step):
            # Find pixels in the current row within the component
            row_pixels = component_mask[y, min_col:max_col].nonzero()[0]
            if row_pixels.size == 0:
                continue
            x_start = min_col + row_pixels.min()
            x_end = min_col + row_pixels.max()

            # Alternate direction for each row for efficient traversal
            if (y - min_row) // step % 2 == 0:
                waypoints.append((x_start, y))
                waypoints.append((x_end, y))
            else:
                waypoints.append((x_end, y))
                waypoints.append((x_start, y))

    return waypoints, labeled_image

def plot_waypoints(image_rgb, waypoints, labeled_image):
    """
    Plots the original image with waypoints overlaid.

    Parameters:
    - image_rgb: NumPy array of shape (H, W, 3), the input RGB image.
    - waypoints: List of (x, y) tuples representing the robot's path.
    - labeled_image: NumPy array with labeled connected components.
    """
    plt.figure(figsize=(10, 10))
    plt.imshow(image_rgb)
    plt.title('Image with Fill Waypoints')

    # Extract x and y coordinates from waypoints
    if not waypoints:
        print("No waypoints to display.")
        return

    x_coords, y_coords = zip(*waypoints)

    # Plot waypoints
    plt.plot(x_coords, y_coords, marker='o', markersize=2, linewidth=1, color='yellow')

    plt.axis('off')
    plt.show()

waypoints, labeled_img = generate_fill_waypoints(img_rgb)
plot_waypoints(img_rgb, waypoints, labeled_img)

"""# **Step 2: Detect and Isolate Image Edges**
###### **s2_generate_edges**

###### The s2_generate_edges function takes an RGB image as input, and iterates through every pixel within the image. For each pixel, the function identifies and tracks the RGBs present within the 2x2 kernel beginning at the pixel itself. If more than one RGB is represented within this four-pixel set, the pixel is deemed an 'edge' and is assigned a value of 255 in the ouput binary image. If the pixel's corresponding 2x2 kernel is monochromatic, it is not considered an edge and assigned a value of 0. Note that the effectiveness of this function is dependent on having already reduced the image's original RGB set. Providing this function with a raw image may lead to all pixel assignments as 'edges' due to subtle variability in RGB values.
"""

img_edges = s2_generate_edges(img_reduced_rgb, display=True)

"""# **Step 3: Group Adjacent Edge Pixels**
###### **s3_group_edges**

###### The s3_group_edges function takes the binary edges image and separate the pixels into independent edges using cv2.connectedComponents. The function iterates through the identified 'connected components' and establishes it as a valid 'edge' if it contains more than edge_threshold = 50 pixels. Each edge is represented as an array of y and x coordinate tuples. These edges are combined in a list and returned by the function.
"""

grouped_edges = s3_group_edges(img_edges, edge_threshold=min_points_per_edge)

fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(12, 5))
axes[0].scatter(grouped_edges[0][:, 1], grouped_edges[0][:, 0], color='blue', s=5)
axes[0].invert_yaxis()
axes[0].set_title('Edge Group 1')
axes[1].scatter(grouped_edges[1][:, 1], grouped_edges[1][:, 0], color='red', s=5)
axes[1].invert_yaxis()
axes[1].set_title('Edge Group 2')
axes[2].scatter(grouped_edges[0][:, 1], grouped_edges[0][:, 0], color='blue', s=5)
axes[2].scatter(grouped_edges[1][:, 1], grouped_edges[1][:, 0], color='red', s=5)
axes[2].invert_yaxis()
axes[2].set_title('All Edge Groups Combined')
plt.tight_layout()
plt.show()

"""# **Step 4: Order Edges**
###### **s4_order_edges**

###### The s4_order_edges command takes unordered edges as a list of arrays (edges) of tuples (pixels in the edges) and outputs the same edges with pixels ordered in a manner desirable for our robot movement. Ideally, the lines can be drawn in a continuous fashion for as long as possible before moving to a separate edge.

###### The algorithm begins by arbitrarily selecting a starting pixel. It then iteratively adds its closest pixel to the list of pixels and updates its current pixel until there are no longer untraversed pixels within a set distance. At this stage, the algorithm reverts to the original starting pixel and runs the same algorithm, adding pixels to the start of the pixel list instead, once again until there are no longer untraversed pixels within the distance range. This list of pixels is added to the full waypoints list and a new starting position is selected.

###### This ensures that complex multi-color image edges are able to processed, including edges that have multiple line intersections.
"""

ordered_edges = s4_order_edges(grouped_edges, dist_thresh=max_dist_betw_points, section_size_thresh=min_section_size)

fig, axes = plt.subplots(nrows=1, ncols=4, figsize=(13, 5))
axes[0].plot(grouped_edges[0][:, 1], grouped_edges[0][:, 0], color='black', lw=.05)
axes[0].invert_yaxis()
axes[0].set_title('Simulated Path of Unordered Edge Group 1', fontsize=10)
axes[1].plot(np.array(ordered_edges[0][0])[:, 1], np.array(ordered_edges[0][0])[:, 0], color='black')
axes[1].invert_yaxis()
axes[1].set_title('Simulated Path of Ordered Edge Group 1', fontsize=10)
axes[2].plot(grouped_edges[1][:, 1], grouped_edges[1][:, 0], color='black', lw=.05)
axes[2].invert_yaxis()
axes[2].set_title('Simulated Path of Unordered Edge Group 2', fontsize=10)
axes[3].plot(np.array(ordered_edges[1][0])[:, 1], np.array(ordered_edges[1][0])[:, 0], color='black')
axes[3].invert_yaxis()
axes[3].set_title('Simulated Path of Ordered Edge Group 2', fontsize=10)
plt.tight_layout()
plt.show()

"""## **4.1:  Ordering Edges with Complicated Input**"""

sys.setrecursionlimit(20000)
mw2_path = '/content/drive/Shareddrives/Senior Design :D/Code/minnesota_wild.png'
mw2_k = 5
mw2_border_size = 2
mw2_min_points_per_edge = 50
mw2_max_dist_betw_points = 5
mw2_min_section_size = 10
mw2_img_rgb = s0_prepare_img(mw2_path, border_size=mw2_border_size, display=False)
mw2_img_reduced_rgb = s1_reduce_img_rgbs(mw2_img_rgb, k=mw2_k, display=True)
mw2_img_edges = s2_generate_edges(mw2_img_reduced_rgb, display=False)
mw2_grouped_edges = s3_group_edges(mw2_img_edges, edge_threshold=mw2_min_points_per_edge)
mw2_ordered_edges = s4_order_edges(mw2_grouped_edges, dist_thresh=mw2_max_dist_betw_points, section_size_thresh=mw2_min_section_size)

plt.imshow(mw2_img_edges)

fig, axes = plt.subplots(nrows=2, ncols=4, figsize=(13, 5))
axes[0, 0].plot(mw2_grouped_edges[0][:, 1], mw2_grouped_edges[0][:, 0], color='black', lw=.03)
axes[0, 0].invert_yaxis()
axes[0, 0].set_title('Simulated Path of Unordered Edge Group 1', fontsize=10)
axes[0, 1].plot(np.array(mw2_ordered_edges[0][0])[:, 1], np.array(mw2_ordered_edges[0][0])[:, 0], color='black')
axes[0, 1].invert_yaxis()
axes[0, 1].set_title('Simulated Path of Ordered Edge Group 1', fontsize=10)
axes[0, 2].plot(mw2_grouped_edges[1][:, 1], mw2_grouped_edges[1][:, 0], color='black', lw=.03)
axes[0, 2].invert_yaxis()
axes[0, 2].set_title('Simulated Path of Unordered Edge Group 2', fontsize=10)
axes[0, 3].plot(np.array(mw2_ordered_edges[1][0])[:, 1], np.array(mw2_ordered_edges[1][0])[:, 0], color='black')
axes[0, 3].plot(np.array(mw2_ordered_edges[1][1])[:, 1], np.array(mw2_ordered_edges[1][1])[:, 0], color='black')
axes[0, 3].invert_yaxis()
axes[0, 3].set_title('Simulated Path of Ordered Edge Group 2', fontsize=10)

axes[1, 0].plot(mw2_grouped_edges[2][:, 1], mw2_grouped_edges[2][:, 0], color='black', lw=.03)
axes[1, 0].invert_yaxis()
axes[1, 0].set_title('Simulated Path of Unordered Edge Group 3', fontsize=10)
axes[1, 1].plot(np.array(mw2_ordered_edges[2][0])[:, 1], np.array(mw2_ordered_edges[2][0])[:, 0], color='black', label='Section 1')
axes[1, 1].plot(np.array(mw2_ordered_edges[2][1])[:, 1], np.array(mw2_ordered_edges[2][1])[:, 0], color='orange', label='Section 2')
axes[1, 1].plot(np.array(mw2_ordered_edges[2][2])[:, 1], np.array(mw2_ordered_edges[2][2])[:, 0], color='green', label='Section 3')
axes[1, 1].plot(np.array(mw2_ordered_edges[2][3])[:, 1], np.array(mw2_ordered_edges[2][3])[:, 0], color='orange')
axes[1, 1].invert_yaxis()
axes[1, 1].set_title('Simulated Path of Ordered Edge Group 3', fontsize=10)
axes[1, 1].legend(loc='upper left', prop={'size': 6})
axes[1, 2].plot(mw2_grouped_edges[3][:, 1], mw2_grouped_edges[3][:, 0], color='black', lw=.03)
axes[1, 2].invert_yaxis()
axes[1, 2].set_title('Simulated Path of Unordered Edge Group 4', fontsize=10)
axes[1, 3].plot(np.array(mw2_ordered_edges[3][0])[:, 1], np.array(mw2_ordered_edges[3][0])[:, 0], color='black')
axes[1, 3].invert_yaxis()
axes[1, 3].set_title('Simulated Path of Ordered Edge Group 4', fontsize=10)
plt.tight_layout()
plt.show()

plt.figure(figsize=(7, 5))
plt.plot(np.array(mw2_ordered_edges[0][0])[:, 1], np.array(mw2_ordered_edges[0][0])[:, 0], color='black')
plt.plot(np.array(mw2_ordered_edges[1][0])[:, 1], np.array(mw2_ordered_edges[1][0])[:, 0], color='blue')
plt.plot(np.array(mw2_ordered_edges[2][0])[:, 1], np.array(mw2_ordered_edges[2][0])[:, 0], color='red')
plt.plot(np.array(mw2_ordered_edges[2][1])[:, 1], np.array(mw2_ordered_edges[2][1])[:, 0], color='red')
plt.plot(np.array(mw2_ordered_edges[2][2])[:, 1], np.array(mw2_ordered_edges[2][2])[:, 0], color='red')
plt.plot(np.array(mw2_ordered_edges[2][3])[:, 1], np.array(mw2_ordered_edges[2][3])[:, 0], color='red')
plt.plot(np.array(mw2_ordered_edges[3][0])[:, 1], np.array(mw2_ordered_edges[3][0])[:, 0], color='green')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()

"""# **Step 5: Simplify Edge Pixels to Waypoints**
###### **s5_simplify_path**

###### The s5_simplify_path function uses the Ramer-Douglas-Peucker algorithm to reduce the number of points in a curve/edge while prserving its overall shape, therefore creating a list of waypoints that can sufficiently represent the image eduges while being distant from one another to allow robot following. The algorithm takes as input the first and last points of the edge. It then calculates the shortest distance between other points and the line between the first and last points for all points. It takes the point with the greatest distance, compares it to the predetermined epsilon thresold value, and keeps it if the distance exceeds it. The curve is the split into two segments, between the first point and the new point, and between the new point and the final point. The algorithm is run for the two new line segments and all subsequently generated line segments until all new possible points are within the epsilon threshold distance away from the curve.
"""

simplified_paths = s5_simplify_path(ordered_edges, epsilon=1.4)

fig, axes = plt.subplots(nrows=1, ncols=4, figsize=(13, 5))
axes[0].plot(np.array(ordered_edges[0][0])[:, 1], np.array(ordered_edges[0][0])[:, 0], color='black')
axes[0].scatter(np.array(ordered_edges[0][0])[:, 1], np.array(ordered_edges[0][0])[:, 0], color='red')
axes[0].invert_yaxis()
axes[0].set_title('Unsimplified Waypoints Shape 1', fontsize=10)

axes[1].plot(np.array(simplified_paths[0])[:, 1], np.array(simplified_paths[0])[:, 0], color='black')
axes[1].scatter(np.array(simplified_paths[0])[:, 1], np.array(simplified_paths[0])[:, 0], color='blue')
axes[1].invert_yaxis()
axes[1].set_title('Simplified Waypoints Shape 1', fontsize=10)

axes[2].plot(np.array(ordered_edges[1][0])[:, 1], np.array(ordered_edges[1][0])[:, 0], color='black')
axes[2].scatter(np.array(ordered_edges[1][0])[:, 1], np.array(ordered_edges[1][0])[:, 0], color='red')
axes[2].invert_yaxis()
axes[2].set_title('Unsimplified Waypoints Shape 2', fontsize=10)

axes[3].plot(np.array(simplified_paths[1])[:, 1], np.array(simplified_paths[1])[:, 0], color='black')
axes[3].scatter(np.array(simplified_paths[1])[:, 1], np.array(simplified_paths[1])[:, 0], color='blue')
axes[3].invert_yaxis()
axes[3].set_title('Simplified Waypoints Shape 2', fontsize=10)

unsimplified_length_1 = len(np.array(ordered_edges[0][0]).flatten())
simplified_length_1 = len(np.array(simplified_paths[0]).flatten())
unsimplified_length_2 = len(np.array(ordered_edges[1][0]).flatten())
simplified_length_2 = len(np.array(simplified_paths[1]).flatten())
print('Shape 1 Number of Waypoints (Unsimplified): ', unsimplified_length_1)
print('Shape 1 Number of Waypoints (Simplified): ', simplified_length_1)
print('Shape 1 Waypoint % Reduction: ', round((1 - (simplified_length_1 / unsimplified_length_1)) * 100, 4))
print('\n')
print('Shape 2 Number of Waypoints (Unsimplified): ', unsimplified_length_2)
print('Shape 2 Number of Waypoints (Simplified): ', simplified_length_2)
print('Shape 2 Waypoint % Reduction: ', round((1 - (simplified_length_2 / unsimplified_length_2)) * 100, 4))
print('\n')
print('Total Waypoint % Reduction: ', round((1 - (simplified_length_1 + simplified_length_2) / (unsimplified_length_1 + unsimplified_length_2)) * 100, 4))

"""# **Step 6: Generate Output File**
###### **s6_generate output**

###### The s6_generate_output function properly extracts the path coordinates, adds paint toggle instructions to the first and last waypoints of each edge segment, and writes this to a predetermined file location to be sent to the robot's onboard computer.
"""

s6_generate_output(simplified_paths, waypoints_output_filename)

"""# **Extra: Fun Animation!**"""

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib notebook
s7_animate_output([np.array(x) for x in simplified_paths], animation_output_filename)