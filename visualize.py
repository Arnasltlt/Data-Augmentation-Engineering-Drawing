import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

def convert_dxf_to_png(dxf_path, png_path):
    """
    Converts a DXF file to a PNG image.
    """
    try:
        print(f"Loading DXF from: {dxf_path}")
        # Load the DXF document
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        print("DXF loaded successfully.")

        # Create a matplotlib backend
        print("Creating matplotlib backend...")
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)

        # Render the DXF
        print("Rendering DXF...")
        Frontend(ctx, out).draw_layout(msp, finalize=True)
        print("DXF rendered.")

        # Save the figure
        print(f"Saving PNG to: {png_path}")
        fig.savefig(png_path, dpi=300)
        plt.close(fig)
        print(f"Successfully converted {dxf_path} to {png_path}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # Example usage:
    # convert_dxf_to_png('my_drawing.dxf', 'my_drawing.png')
    pass
