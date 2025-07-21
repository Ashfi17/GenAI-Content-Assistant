# GenAI-Content-Assistant

An AI-powered content creation tool that generates campaign assets with A/B testing capabilities using Google's Gemini and Imagen APIs.

## Features

- **Campaign Asset Generation**: Create slogans, image prompts, color palettes, and font recommendations
- **Real Image Generation**: Uses Google Imagen 3.0/4.0 for actual image creation
- **A/B Testing**: Generate multiple creative variants with simulated performance metrics
- **Export Functionality**: Download campaign briefs as JSON and images as ZIP files

## Setup

### Prerequisites

- Python 3.8+
- Google Cloud Account with billing enabled
- Gemini API access
- Vertex AI API enabled in your Google Cloud Project

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Ashfi17/GenAI-Content-Assistant.git
cd genai-content-assistant
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

## Configuration

The app requires:

1. **Gemini API Key** - For text generation
2. **Google Cloud Project ID** - For image generation
3. **Location** - Cloud region (default: us-central1)

## API Models Used

- **Text Generation**: `gemini-2.0-flash`
- **Image Generation**:
  - Primary: `imagen-3.0-generate-002`
  - Fallback: `imagen-4.0-generate-preview-06-06`

## Usage Example

1. Enter a creative brief: _"Launch promo for fantasy football app targeting Gen Z with meme culture and high-energy visuals"_
2. Generate 2 creative variants with different approaches
3. Generate actual images using Imagen API
4. Compare variants with simulated A/B testing metrics
5. Export campaign assets and images
