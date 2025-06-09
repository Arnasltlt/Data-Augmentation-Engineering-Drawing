# DXF Symbol Library Usage

## Library Information
- **File:** symbols.dxf
- **Generated:** 1749501019.3460572
- **Symbols:** 78 blocks available

## Usage in generator.py

Instead of the current SVG conversion approach, you can now use proper DXF blocks:

```python
# Load the symbol library (do this once)
symbol_lib = ezdxf.readfile('library/symbols.dxf')

# Insert a symbol block
def insert_symbol_block(msp, symbol_name, location, scale=1.0, rotation=0):
    if symbol_name in symbol_lib.blocks:
        msp.add_blockref(symbol_name, location, dxfattribs={
            'xscale': scale,
            'yscale': scale, 
            'rotation': rotation
        })
        return True
    return False

# Example usage
insert_symbol_block(msp, 'gdt_flatness', (100, 50), scale=1.2)
```

## Available Symbols

The following blocks are available in this library:

- `gdt_flatness` (8.0×8.0mm)
- `gdt_straightness` (8.0×8.0mm)
- `gdt_circularity` (8.0×8.0mm)
- `gdt_cylindricity` (8.0×8.0mm)
- `gdt_angularity` (8.0×8.0mm)
- `gdt_parallelism` (8.0×8.0mm)
- `gdt_perpendicularity` (8.0×8.0mm)
- `gdt_position` (8.0×8.0mm)
- `gdt_concentricity` (8.0×8.0mm)
- `gdt_symmetry` (8.0×8.0mm)
- `gdt_profile_line` (8.0×8.0mm)
- `gdt_profile_surface` (8.0×8.0mm)
- `gdt_runout_circular` (8.0×8.0mm)
- `gdt_runout_total` (8.0×8.0mm)
- `diameter_symbol` (6.0×6.0mm)
- `radius_symbol` (6.0×6.0mm)
- `spherical_diameter` (8.0×6.0mm)
- `spherical_radius` (8.0×6.0mm)
- `square_symbol` (6.0×6.0mm)
- `arc_length` (8.0×6.0mm)
- `depth_symbol` (6.0×6.0mm)
- `slope` (10.0×6.0mm)
- `surface_triangle` (6.0×6.0mm)
- `surface_roughness_ra` (8.0×6.0mm)
- `surface_machining_required` (6.0×6.0mm)
- `surface_machining_prohibited` (6.0×6.0mm)
- `surface_lay_parallel` (6.0×6.0mm)
- `surface_lay_perpendicular` (6.0×6.0mm)
- `surface_lay_angular` (6.0×6.0mm)
- `surface_lay_multidirectional` (6.0×6.0mm)
- `thread_metric` (20.0×8.0mm)
- `thread_imperial` (20.0×8.0mm)
- `thread_pipe` (20.0×8.0mm)
- `weld_fillet` (10.0×6.0mm)
- `weld_groove` (10.0×6.0mm)
- `weld_groove_bevel` (10.0×6.0mm)
- `weld_groove_u` (10.0×6.0mm)
- `weld_groove_v` (10.0×6.0mm)
- `weld_plug` (10.0×6.0mm)
- `weld_spot` (8.0×8.0mm)
- `weld_seam` (10.0×6.0mm)
- `weld_back` (10.0×6.0mm)
- `weld_all_around` (8.0×8.0mm)
- `weld_field` (8.0×8.0mm)
- `counterbore` (8.0×6.0mm)
- `counterbore_symbol` (6.0×6.0mm)
- `countersink` (8.0×6.0mm)
- `countersink_symbol` (6.0×6.0mm)
- `spotface_symbol` (8.0×6.0mm)
- `frame_left` (2.0×8.0mm)
- `frame_right` (2.0×8.0mm)
- `frame_separator` (1.0×8.0mm)
- `frame_datum_target` (8.0×8.0mm)
- `centerline` (15.0×2.0mm)
- `center_line` (15.0×2.0mm)
- `hidden_line` (15.0×2.0mm)
- `phantom_line` (15.0×2.0mm)
- `break_line_long` (20.0×4.0mm)
- `break_line_short` (8.0×4.0mm)
- `cutting_plane` (20.0×4.0mm)
- `section_line_a` (8.0×8.0mm)
- `section_line_b` (8.0×8.0mm)
- `view_arrow` (8.0×6.0mm)
- `section_pattern` (10.0×10.0mm)
- `revision_cloud` (12.0×8.0mm)
- `revision_triangle` (6.0×6.0mm)
- `measurement_point` (4.0×4.0mm)
- `inspection_stamp` (8.0×8.0mm)
- `critical_dimension` (10.0×6.0mm)
- `reference_dimension` (10.0×6.0mm)
- `statistical_tolerance` (12.0×6.0mm)
- `projected_tolerance_zone` (8.0×8.0mm)
- `conical_taper` (12.0×6.0mm)
- `scale_indicator` (15.0×4.0mm)
- `title_block_corner` (8.0×8.0mm)
- `title_block_line_h` (20.0×1.0mm)
- `title_block_line_v` (1.0×20.0mm)
- `title_block_text` (25.0×6.0mm)

## Integration Notes

1. **Performance:** Using DXF blocks is much more efficient than converting SVG at runtime
2. **Quality:** Blocks preserve the exact geometry from the SVG files
3. **CAD Standard:** This follows standard CAD practices for symbol libraries
4. **Scaling:** Blocks can be scaled and rotated without quality loss

## Next Steps

Update `generator.py` to use this library instead of the current SVG conversion approach.
