import requests
import random
import json

class ColormindAPI:
    def __init__(self, model="default"):
        self.url = "http://colormind.io/api/"
        self.model = model

    def generate_palette(self, input_colors=None):
        """
        Generate a color palette using the Colormind API.

        :param input_colors: A list of RGB tuples or 'N' (None) values.
                             For example: [(44, 43, 44), (90, 83, 82), 'N', 'N', 'N']
                             The list should contain exactly 5 elements.
        :return: A list of 5 RGB tuples representing the color palette.
        """
        if input_colors is None:
            # Default input for generating a palette
            input_colors = ["N", "N", "N", "N", "N"]

        if len(input_colors) != 5:
            raise ValueError("Input must be a list of 5 elements (RGB tuples or 'N').")

        # Prepare the payload for the API request
        payload = {
            "input": input_colors,
            "model": self.model
        }

        # Send the request to the Colormind API
        try:
            response = requests.post(self.url, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            return result["result"]
        except requests.RequestException as e:
            print(f"Error fetching color palette: {e}")
            return None

    def generate_palette_from_image(self, image_url):
        """
        Generate a color palette based on the colors extracted from an image.

        :param image_url: URL of the image from which to extract the colors.
        :return: A list of 5 RGB tuples representing the color palette.
        """
        # For the purpose of this example, we'll simulate extracting dominant colors from the image
        # You might need an actual color extraction method for a real-world scenario

        # Simulate extracting two dominant colors from the image
        dominant_colors = [
            tuple(random.randint(0, 255) for _ in range(3)),
            tuple(random.randint(0, 255) for _ in range(3))
        ]

        # Use the dominant colors as input and let the Colormind API generate the rest
        input_colors = [dominant_colors[0], dominant_colors[1], 'N', 'N', 'N']
        return self.generate_palette(input_colors)

# Example usage
if __name__ == "__main__":
    colormind = ColormindAPI()
    
    # Example 1: Generate a random color palette
    palette = colormind.generate_palette()
    print("Generated Palette:", palette)
    
    # Example 2: Generate a palette from image colors
    image_palette = colormind.generate_palette_from_image("http://example.com/path/to/album/cover.jpg")
    print("Generated Palette from Image:", image_palette)
