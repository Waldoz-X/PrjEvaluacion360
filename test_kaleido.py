import plotly.graph_objects as go
import plotly.io as pio
import signal

# Timeout handler
def handler(signum, frame):
    raise Exception("Timeout reached")

# Register the signal function handler
# Windows doesn't support signal.SIGALRM, so we just run it and hope.
# We'll use a simple print to debug progress.

print("Starting Kaleido test...")
try:
    fig = go.Figure(data=go.Bar(y=[1, 2, 3]))
    print("Figure created. Converting to image...")
    # Use default scale and dimensions
    img_bytes = pio.to_image(fig, format="png")
    print(f"Kaleido test successful: Image generated ({len(img_bytes)} bytes).")
except Exception as e:
    print(f"Kaleido test failed: {e}")
