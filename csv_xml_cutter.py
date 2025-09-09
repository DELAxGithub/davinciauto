#!/usr/bin/env python3
"""
CSV + XML Timeline Cutter
Takes existing Premiere XML and cuts it based on CSV timecodes
"""

import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import os
import sys

# Try to import tkinter, fall back to command line if not available
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    HAS_GUI = True
except ImportError:
    HAS_GUI = False


def timecode_to_frames(timecode, fps=30):
    """Convert timecode string to frame number"""
    if not timecode or timecode.strip() == '':
        return 0
    
    # Handle both : and ; separators
    parts = timecode.replace(';', ':').split(':')
    
    if len(parts) == 4:  # HH:MM:SS:FF
        hours, minutes, seconds, frames = map(int, parts)
    elif len(parts) == 3:  # MM:SS:FF
        hours = 0
        minutes, seconds, frames = map(int, parts)
    elif len(parts) == 2:  # SS:FF
        hours = minutes = 0
        seconds, frames = map(int, parts)
    else:
        return 0
    
    total_frames = (hours * 3600 + minutes * 60 + seconds) * fps + frames
    return total_frames


def frames_to_ppro_ticks(frames, fps=30):
    """Convert frames to Premiere Pro ticks (254016000000 per second)"""
    seconds = frames / fps
    return int(seconds * 254016000000)


def csv_color_to_premiere_label(csv_color):
    """Convert CSV color to Premiere Pro label"""
    # 直接Premiere Proラベル名を使用（GASと統一）
    valid_labels = [
        'Violet', 'Rose', 'Mango', 'Yellow', 'Lavender', 'Caribbean', 
        'Tan', 'Forest', 'Blue', 'Purple', 'Teal', 'Brown', 'Gray',
        'Iris', 'Cerulean', 'Magenta'
    ]
    
    # 古い色名からの変換マッピング（後方互換性のため）
    legacy_color_map = {
        'rose': 'Rose',
        'pink': 'Rose', 
        'cyan': 'Caribbean',
        'blue': 'Blue',
        'mint': 'Mango',
        'green': 'Forest',
        'yellow': 'Yellow',
        'orange': 'Mango',
        'red': 'Rose',
        'purple': 'Purple',
        'brown': 'Brown',
        'gray': 'Gray',
        'lavender': 'Lavender',
        'tan': 'Tan',
        'teal': 'Teal',
        'magenta': 'Magenta',
        'violet': 'Violet',
        'forest': 'Forest',
        'iris': 'Iris',
        'cerulean': 'Cerulean',
        'caribbean': 'Caribbean',
        'mango': 'Mango'
    }
    
    # 空の場合はデフォルト
    if not csv_color or csv_color.strip() == '':
        return 'Caribbean'
    
    # そのままPremiereラベル名として有効かチェック
    if csv_color in valid_labels:
        return csv_color
    
    # 古い色名から変換
    return legacy_color_map.get(csv_color.lower(), 'Caribbean')


def extract_audio_files_from_xml(xml_file_path):
    """Extract audio file information from existing XML"""
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    audio_files = []
    
    # Find all clipitems with file references
    for clipitem in root.findall('.//clipitem'):
        file_elem = clipitem.find('file')
        if file_elem is not None:
            name_elem = file_elem.find('name')
            pathurl_elem = file_elem.find('pathurl')
            
            if name_elem is not None and pathurl_elem is not None:
                file_info = {
                    'name': name_elem.text,
                    'pathurl': pathurl_elem.text
                }
                # Find the full file definition in the media section
                file_id = file_elem.get('id')
                full_file_elem = root.find(f".//media/file[@id='{file_id}']")
                if full_file_elem is not None:
                    file_info['element'] = full_file_elem
                else:
                    # Fallback for inline file definitions
                    file_info['element'] = file_elem
                
                # Avoid duplicates
                if not any(f['name'] == file_info['name'] for f in audio_files):
                    audio_files.append(file_info)
    
    print(f"XMLから抽出したファイル: {len(audio_files)}個")
    for i, file_info in enumerate(audio_files):
        print(f"  {i+1}: {file_info['name']}")
    
    return audio_files


def create_cut_xml_from_template(csv_file_path, template_xml_path):
    """Create cut XML using template XML structure and CSV timecodes"""
    
    # Extract audio files from template XML
    audio_files = extract_audio_files_from_xml(template_xml_path)
    
    if not audio_files:
        print("エラー: テンプレートXMLからオーディオファイルが見つかりません")
        return None
    
    # Parse template XML to get structure
    template_tree = ET.parse(template_xml_path)
    template_root = template_tree.getroot()
    
    # Create new XML with same structure
    root = ET.Element('xmeml', version='4')
    
    # Copy sequence structure from template
    template_sequence = template_root.find('sequence')
    sequence = ET.SubElement(root, 'sequence')
    
    # Copy all sequence attributes
    for attr_name, attr_value in template_sequence.attrib.items():
        sequence.set(attr_name, attr_value)
    
    # Generate new UUID
    uuid_elem = ET.SubElement(sequence, 'uuid')
    uuid_elem.text = str(uuid.uuid4())
    
    # Duration (will be updated later)
    duration = ET.SubElement(sequence, 'duration')
    duration.text = '15155'
    
    # Copy rate from template
    template_rate = template_sequence.find('rate')
    if template_rate is not None:
        rate = ET.SubElement(sequence, 'rate')
        for child in template_rate:
            new_child = ET.SubElement(rate, child.tag)
            new_child.text = child.text
    
    # Name
    name_elem = ET.SubElement(sequence, 'name')
    name_elem.text = f"{os.path.splitext(os.path.basename(csv_file_path))[0]}_cut"
    
    # Copy media structure from template
    template_media = template_sequence.find('media')
    media = ET.SubElement(sequence, 'media')
    
    # Copy video section completely
    template_video = template_media.find('video')
    if template_video is not None:
        video = ET.SubElement(media, 'video')
        # Copy all video content
        for child in template_video:
            video.append(child)
    
    # Copy audio structure but replace clipitems
    template_audio = template_media.find('audio')
    audio = ET.SubElement(media, 'audio')
    
    # Copy audio format and outputs
    for child in template_audio:
        if child.tag != 'track':
            audio.append(child)
    
    # Read CSV and group by color blocks
    color_blocks = []
    current_color = None
    current_block = None
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            speaker = row.get('Speaker Name', '').strip()
            in_point = row.get('イン点', '').strip()
            out_point = row.get('アウト点', '').strip()
            text = row.get('文字起こし', '').strip()
            color = row.get('色選択', '').strip()
            
            # 色が指定されていない行や、タイムコードがない行はスキップ
            if not in_point or not out_point or not color:
                continue
            
            # Convert timecodes to frames
            in_frames = timecode_to_frames(in_point)
            out_frames = timecode_to_frames(out_point)
            
            if in_frames >= out_frames:
                continue
            
            # If color changed, start new block
            if color != current_color:
                if current_block:
                    color_blocks.append(current_block)
                
                current_color = color
                current_block = {
                    'color': color,
                    'start_frames': in_frames,
                    'end_frames': out_frames,
                    'rows': [row]
                }
            else:
                # Extend current block
                current_block['end_frames'] = out_frames
                current_block['rows'].append(row)
        
        # Add last block
        if current_block:
            color_blocks.append(current_block)
    
    print(f"検出された色ブロック: {len(color_blocks)}個")
    for i, block in enumerate(color_blocks):
        print(f"ブロック{i+1}: {block['color']} ({block['start_frames']} - {block['end_frames']}) = {block['end_frames'] - block['start_frames']}フレーム")
    
    # Create audio tracks based on template
    template_tracks = template_audio.findall('track')
    gap_size = 149  # Like original
    
    for track_idx, template_track in enumerate(template_tracks):
        if track_idx >= len(audio_files):
            # Empty track
            track = ET.SubElement(audio, 'track')
            # Copy all attributes
            for attr_name, attr_value in template_track.attrib.items():
                track.set(attr_name, attr_value)
            # Copy non-clipitem children
            for child in template_track:
                if child.tag != 'clipitem':
                    track.append(child)
            continue
        
        # Create track with clipitems
        track = ET.SubElement(audio, 'track')
        # Copy all attributes
        for attr_name, attr_value in template_track.attrib.items():
            track.set(attr_name, attr_value)
        
        # Create clipitems for this track
        clip_counter = track_idx * len(color_blocks) + 1
        timeline_position = 0
        audio_file = audio_files[track_idx]
        
        for block_idx, block in enumerate(color_blocks):
            start_frames = block['start_frames']
            end_frames = block['end_frames']
            duration_frames = end_frames - start_frames
            
            # Create clipitem
            clipitem = ET.SubElement(track, 'clipitem')
            clipitem.set('id', f'clipitem-{clip_counter}')
            clipitem.set('premiereChannelType', 'mono')
            
            # Master clip ID
            masterclipid = ET.SubElement(clipitem, 'masterclipid')
            masterclipid.text = f'masterclip-{track_idx + 1}'
            
            # Name
            clip_name = ET.SubElement(clipitem, 'name')
            clip_name.text = audio_file['name']
            
            # Enabled
            enabled = ET.SubElement(clipitem, 'enabled')
            enabled.text = 'TRUE'
            
            # Duration (total file duration - estimated)
            clip_duration = ET.SubElement(clipitem, 'duration')
            clip_duration.text = str(end_frames)
            
            # Rate
            clip_rate = ET.SubElement(clipitem, 'rate')
            clip_timebase = ET.SubElement(clip_rate, 'timebase')
            clip_timebase.text = '30'
            clip_ntsc = ET.SubElement(clip_rate, 'ntsc')
            clip_ntsc.text = 'TRUE'
            
            # Start and end in timeline
            start = ET.SubElement(clipitem, 'start')
            start.text = str(timeline_position)
            
            end = ET.SubElement(clipitem, 'end')
            end.text = str(timeline_position + duration_frames)
            
            # In and out of source media
            clip_in = ET.SubElement(clipitem, 'in')
            clip_in.text = str(start_frames)
            
            clip_out = ET.SubElement(clipitem, 'out')
            clip_out.text = str(end_frames)
            
            # Premiere Pro ticks
            ppro_ticks_in = ET.SubElement(clipitem, 'pproTicksIn')
            ppro_ticks_in.text = str(frames_to_ppro_ticks(start_frames))
            
            ppro_ticks_out = ET.SubElement(clipitem, 'pproTicksOut')
            ppro_ticks_out.text = str(frames_to_ppro_ticks(end_frames))
            
            # File reference
            file_elem = ET.SubElement(clipitem, 'file')
            file_elem.set('id', f'file-{track_idx + 1}')

            # Copy file metadata from template for accuracy
            if 'element' in audio_file and audio_file['element'] is not None:
                for child in audio_file['element']:
                    file_elem.append(child)
            else: # Fallback to basic info
                ET.SubElement(file_elem, 'name').text = audio_file['name']
                ET.SubElement(file_elem, 'pathurl').text = audio_file['pathurl']
            
            # Labels - CSVの色選択を反映
            labels = ET.SubElement(clipitem, 'labels')
            label2 = ET.SubElement(labels, 'label2')
            premiere_label = csv_color_to_premiere_label(block['color'])
            label2.text = premiere_label
            
            print(f"A{track_idx + 1}トラック: ブロック{clip_counter} ({timeline_position} - {timeline_position + duration_frames}) - {audio_file['name']} [ラベル: {premiere_label}]")
            
            # Update timeline position with gap
            timeline_position += duration_frames + gap_size
            clip_counter += 1
        
        # Copy non-clipitem children from template
        for child in template_track:
            if child.tag != 'clipitem':
                track.append(child)
    
    # Update sequence duration
    total_duration = timeline_position - gap_size if color_blocks else 0
    duration.text = str(total_duration)
    
    return root


def prettify_xml(elem):
    """Return a pretty-printed XML string with DOCTYPE"""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    xml_string = reparsed.toprettyxml(indent="\t", encoding='UTF-8').decode('utf-8')
    
    # Add DOCTYPE declaration
    xml_lines = xml_string.split('\n')
    xml_lines.insert(1, '<!DOCTYPE xmeml>')
    
    return '\n'.join(xml_lines)


def select_files_gui():
    """GUI file selection interface"""
    if not HAS_GUI:
        return None, None
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    try:
        # Select template XML file first
        template_xml_file = filedialog.askopenfilename(
            title="テンプレートXMLファイルを選択してください（例: 021-1.xml）",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if not template_xml_file:
            messagebox.showinfo("キャンセル", "テンプレートXMLファイルが選択されませんでした")
            return None, None
        
        # Select CSV file
        csv_file = filedialog.askopenfilename(
            title="CSVファイルを選択してください",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not csv_file:
            messagebox.showinfo("キャンセル", "CSVファイルが選択されませんでした")
            return None, None
        
        return csv_file, template_xml_file
    
    finally:
        root.destroy()


def main():
    # Check if command line arguments are provided
    if len(sys.argv) >= 3:
        # Command line mode
        csv_file = sys.argv[1]
        template_xml_file = sys.argv[2]
        
        if not os.path.exists(csv_file):
            print(f"Error: CSV file '{csv_file}' not found")
            return
        
        if not os.path.exists(template_xml_file):
            print(f"Error: Template XML file '{template_xml_file}' not found")
            return
    else:
        # GUI mode
        if HAS_GUI:
            print("ファイル選択ダイアログを開きます...")
            csv_file, template_xml_file = select_files_gui()
            
            if not csv_file or not template_xml_file:
                return
            
            print(f"テンプレートXML: {template_xml_file}")
            print(f"CSVファイル: {csv_file}")
        else:
            print("Usage: python csv_xml_cutter.py <csv_file> <template_xml_file>")
            print("Example: python csv_xml_cutter.py 'script.csv' '021-1.xml'")
            print("Note: GUI mode not available (tkinter not installed)")
            return
    
    try:
        # Generate XML
        xml_root = create_cut_xml_from_template(csv_file, template_xml_file)
        
        if xml_root is None:
            return
        
        # Output file
        output_file = f"{os.path.splitext(csv_file)[0]}_cut_from_{os.path.splitext(os.path.basename(template_xml_file))[0]}.xml"
        
        # Write XML with DOCTYPE
        xml_string = prettify_xml(xml_root)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        success_msg = f"XML generated: {output_file}"
        print(f"\n{success_msg}")
        
        # Show success message in GUI mode
        if len(sys.argv) < 3 and HAS_GUI:
            messagebox.showinfo("完了", f"XMLファイルを生成しました:\n{output_file}")
    
    except Exception as e:
        error_msg = f"エラーが発生しました: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # Show error message in GUI mode
        if len(sys.argv) < 3 and HAS_GUI:
            messagebox.showerror("エラー", error_msg)


if __name__ == "__main__":
    main()