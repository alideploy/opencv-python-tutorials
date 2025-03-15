#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Instance Segmentation with Ultralytics YOLOv8
---------------------------------------------
This script demonstrates real-time instance segmentation using YOLOv8 and a webcam.
It includes options for displaying masks, confidence scores, and saving results.
"""

import argparse
import cv2
import time
import numpy as np
from ultralytics import YOLO
from pathlib import Path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YOLOv8 real-time instance segmentation with webcam")
    parser.add_argument("--model", type=str, default="yolov8n-seg.pt", 
                        help="Model to use (yolov8n-seg.pt, yolov8s-seg.pt, yolov8m-seg.pt, yolov8l-seg.pt, yolov8x-seg.pt)")
    parser.add_argument("--device", type=str, default="0", 
                        help="Device to use (webcam index or video path)")
    parser.add_argument("--conf", type=float, default=0.25, 
                        help="Confidence threshold for detections")
    parser.add_argument("--save", action="store_true", 
                        help="Save the output video")
    parser.add_argument("--classes", nargs="+", type=int, 
                        help="Filter by class (e.g., --classes 0 2 3 for person, car, motorcycle)")
    parser.add_argument("--show-fps", action="store_true", 
                        help="Display FPS counter")
    parser.add_argument("--show-labels", action="store_true", default=True,
                        help="Display class labels")
    parser.add_argument("--show-conf", action="store_true", default=True,
                        help="Display confidence scores")
    parser.add_argument("--mask-alpha", type=float, default=0.3,
                        help="Mask transparency (0-1)")
    parser.add_argument("--custom-visualization", action="store_true",
                        help="Use custom visualization instead of built-in")
    return parser.parse_args()


def custom_visualization(frame, results, mask_alpha=0.3):
    """
    Custom visualization of segmentation results.
    
    Args:
        frame: Original frame
        results: YOLOv8 results
        mask_alpha: Transparency of masks (0-1)
    
    Returns:
        Annotated frame with custom visualization
    """
    # Create a copy of the original frame
    annotated_frame = frame.copy()
    
    # Get the masks, boxes, and class IDs
    if results[0].masks is not None:
        masks = results[0].masks.data.cpu().numpy()
        boxes = results[0].boxes.data.cpu().numpy()
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
        
        # Get unique colors for each class
        np.random.seed(42)  # For consistent colors
        colors = np.random.randint(0, 255, size=(len(results[0].names), 3), dtype=np.uint8)
        
        # Draw each mask and box
        for i, (mask, box, class_id) in enumerate(zip(masks, boxes, class_ids)):
            # Get color for this class
            color = colors[class_id].tolist()
            
            # Create binary mask
            mask_binary = cv2.resize(mask, (frame.shape[1], frame.shape[0]))
            mask_binary = (mask_binary > 0.5).astype(np.uint8)
            
            # Create colored mask
            colored_mask = np.zeros_like(frame, dtype=np.uint8)
            colored_mask[mask_binary == 1] = color
            
            # Blend the colored mask with the frame
            annotated_frame = cv2.addWeighted(
                annotated_frame, 
                1, 
                colored_mask, 
                mask_alpha, 
                0
            )
            
            # Draw bounding box
            x1, y1, x2, y2 = map(int, box[:4])
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw class label and confidence
            class_name = results[0].names[class_id]
            confidence = box[4]
            label = f"{class_name} {confidence:.2f}"
            
            # Calculate text size and position
            text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            text_w, text_h = text_size
            
            # Draw label background
            cv2.rectangle(
                annotated_frame, 
                (x1, y1 - text_h - 8), 
                (x1 + text_w + 8, y1), 
                color, 
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated_frame, 
                label, 
                (x1 + 4, y1 - 4), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (255, 255, 255), 
                2
            )
    
    return annotated_frame


def main():
    """Main function for real-time instance segmentation."""
    # Parse arguments
    args = parse_arguments()
    
    # Load the model
    print(f"Loading model: {args.model}...")
    model = YOLO(args.model)
    
    # Open webcam or video file
    try:
        device = int(args.device)  # Try to convert to integer for webcam index
    except ValueError:
        device = args.device  # Use as string path for video file
    
    print(f"Opening video source: {device}...")
    cap = cv2.VideoCapture(device)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source {device}")
        return
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Create output video writer if saving is enabled
    output_writer = None
    if args.save:
        output_path = f"output_{Path(args.model).stem}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        print(f"Saving output to: {output_path}")
    
    # Variables for FPS calculation
    frame_count = 0
    start_time = time.time()
    fps_display = 0
    
    print("Starting segmentation. Press 'q' to quit.")
    
    # Main loop
    while cap.isOpened():
        # Read a frame
        success, frame = cap.read()
        
        if not success:
            print("Error: Failed to read frame")
            break
        
        # Update FPS calculation
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:  # Update FPS every second
            fps_display = frame_count / elapsed_time
            frame_count = 0
            start_time = time.time()
        
        # Run YOLOv8 inference
        results = model(
            frame, 
            conf=args.conf, 
            classes=args.classes,
            verbose=False
        )
        
        # Visualize the results on the frame
        if args.custom_visualization:
            annotated_frame = custom_visualization(frame, results, args.mask_alpha)
        else:
            annotated_frame = results[0].plot(
                conf=args.show_conf,
                labels=args.show_labels,
                line_width=2,
                masks=True,
                boxes=True
            )
        
        # Add FPS counter if enabled
        if args.show_fps:
            cv2.putText(
                annotated_frame, 
                f"FPS: {fps_display:.1f}", 
                (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 255, 0), 
                2
            )
        
        # Display the annotated frame
        cv2.imshow("YOLOv8 Instance Segmentation", annotated_frame)
        
        # Save the frame if enabled
        if output_writer is not None:
            output_writer.write(annotated_frame)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release resources
    cap.release()
    if output_writer is not None:
        output_writer.release()
    cv2.destroyAllWindows()
    
    print("Segmentation finished.")


if __name__ == "__main__":
    main()