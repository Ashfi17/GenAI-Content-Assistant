import streamlit as st
import google.generativeai as genai
import google.genai as genai_client
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import random
import os
import base64
from io import BytesIO
import zipfile
from PIL import Image

from config.settings import GOOGLE_CLOUD_PROJECT_ID,GOOGLE_CLOUD_REGION

# Pydantic Models
class ColorPalette(BaseModel):
    primary: str = Field(description="Primary color with hex code")
    secondary: str = Field(description="Secondary color with hex code")
    accent: str = Field(description="Accent color with hex code")

class CampaignAsset(BaseModel):
    slogan: str = Field(description="Creative campaign slogan")
    image_prompt: str = Field(description="Detailed image generation prompt")
    color_palette: ColorPalette
    font_recommendation: str = Field(description="Recommended font name")

class CampaignVariants(BaseModel):
    variant_a: CampaignAsset
    variant_b: CampaignAsset


# App Configuration
st.set_page_config(
    page_title="GenAI Content Assistant V1",
    page_icon="🎨",
    layout="wide"
)

# Initialize session state
if 'generated_variants' not in st.session_state:
    st.session_state.generated_variants = None
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = {}
if 'genai_client' not in st.session_state:
    st.session_state.genai_client = None

def configure_api():
    """Configure Gemini API and GenAI Client"""
    # Load API keys
    try:
        from dotenv import load_dotenv
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        project_id = GOOGLE_CLOUD_PROJECT_ID  # Default project ID
        location = GOOGLE_CLOUD_REGION  # Default location

        if not GEMINI_API_KEY:
            st.error("GEMINI_API_KEY not found. Please set it in your .env file.")
            st.stop()
    except ModuleNotFoundError:
        GEMINI_API_KEY = st.secrets["API_KEY"]
        project_id = st.secrets["PROJECT_ID"]
        location = st.secrets["LOCATION"]

    # with st.sidebar:
    #     st.subheader("API Configuration")
        # api_key = st.text_input("Enter your Gemini API Key", type="password")
        # project_id = st.text_input("Google Cloud Project ID", placeholder="gen-lang-client-0441709835")
        # location = st.selectbox("Location", ["us-central1", "us-east1", "us-west1"], index=0)
        
    if GEMINI_API_KEY and project_id:
        # Configure traditional Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Configure GenAI Client for Imagen
        try:
            client = genai_client.Client(
                project=project_id,
                location=location
            )
            st.session_state.genai_client = client
            return True
        except Exception as e:
            st.error(f"Error configuring GenAI Client: {e}")
            st.info("Make sure you have set the project ID and location correctly in your .env file.")
            return False
    return False

def generate_campaign_variants(brief: str) -> CampaignVariants:
    """Generate multiple campaign variants using Gemini"""
    
    prompt = f"""
    You are a creative marketing assistant. Based on the following creative brief, generate 2 distinct campaign variants (A, B) with different creative approaches.

    Creative Brief: {brief}

    For each variant, provide:
    1. A unique campaign slogan
    2. A detailed image generation prompt (describe visual style, colors, mood, elements)
    3. A color palette with 3 hex colors (primary, secondary, accent)
    4. A font recommendation

    Make each variant distinctly different in tone and approach:
    - Variant A: Bold and direct approach
    - Variant B: Creative and artistic approach

    Return your response in this exact JSON format:
    {{
        "variant_a": {{
            "slogan": "campaign slogan here",
            "image_prompt": "detailed image description here",
            "color_palette": {{
                "primary": "#hexcode",
                "secondary": "#hexcode", 
                "accent": "#hexcode"
            }},
            "font_recommendation": "font name"
        }},
        "variant_b": {{
            "slogan": "campaign slogan here",
            "image_prompt": "detailed image description here",
            "color_palette": {{
                "primary": "#hexcode",
                "secondary": "#hexcode",
                "accent": "#hexcode"
            }},
            "font_recommendation": "font name"
        }}
    }}
    """

    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    
    # Parse JSON response
    json_str = response.text.strip()
    if json_str.startswith('```json'):
        json_str = json_str[7:-3]
    elif json_str.startswith('```'):
        json_str = json_str[3:-3]
    
    try:
        data = json.loads(json_str)
        return CampaignVariants(**data)
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        st.error(f"Raw response: {response.text}")
        return None

def generate_image(prompt: str, variant_name: str) -> bytes:
    """Generate image using Imagen model via GenAI Client"""
    if not st.session_state.genai_client:
        st.error("GenAI Client not configured. Please check your API settings.")
        return None
        
    try:
        client = st.session_state.genai_client
        model_name = 'models/imagen-4.0-generate-preview-06-06'  # Using the more stable model
        
        # st.info(f"Generating image with {model_name} for prompt: '{prompt[:50]}...'")
        
        response = client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",  # Good for campaign visuals
                safety_filter_level="BLOCK_LOW_AND_ABOVE",
                person_generation="ALLOW_ADULT"
            )
        )

        if response.generated_images and len(response.generated_images) > 0:
            generated_image = response.generated_images[0]
            if generated_image.image and generated_image.image.image_bytes:
                return generated_image.image.image_bytes
            else:
                st.error("No image data in generated response.")
                return None
        else:
            error_msg = "No images were generated."
            if hasattr(response, 'filters') and response.filters:
                error_msg += f" Safety filters may have blocked content: {response.filters}"
            st.error(error_msg)
            return None

    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        
        # Try fallback with imagen-4.0-generate-preview model
        try:
            st.info("Trying fallback model: imagen-4.0-generate-preview-06-06...")
            
            response = client.models.generate_images(
                model='models/imagen-4.0-generate-preview-06-06',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    person_generation="ALLOW_ADULT"
                )
            )
            
            if response.generated_images and len(response.generated_images) > 0:
                generated_image = response.generated_images[0]
                if generated_image.image and generated_image.image.image_bytes:
                    return generated_image.image.image_bytes
                    
        except Exception as e2:
            st.error(f"Both Imagen models failed. Error: {str(e2)}")
            st.info("""
            **Troubleshooting:**
            - Ensure your Google Cloud Project has billing enabled
            - Verify Vertex AI API is enabled
            - Check if Imagen models are available in your region
            """)
            
        return None

def simulate_performance_metrics():
    """Generate simulated A/B testing metrics"""
    return {
        'ctr': round(random.uniform(2.1, 8.5), 2),
        'engagement': round(random.uniform(15, 45), 1),
        'conversion': round(random.uniform(1.2, 4.8), 2)
    }

def display_variant_card(variant: CampaignAsset, variant_name: str, metrics: Dict):
    """Display a campaign variant card"""
    with st.container():
        st.subheader(f"🎯 Variant {variant_name}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Slogan
            st.markdown("**Campaign Slogan:**")
            st.markdown(f"*\"{variant.slogan}\"*")

             # Image prompt
            with st.expander("View Image Prompt"):
                st.write(variant.image_prompt)
            
            # Image
            st.markdown("**Generated Image:**")
            if variant_name not in st.session_state.generated_images:
                if st.button(f"Generate Image for Variant {variant_name}", key=f"gen_{variant_name}"):
                    with st.spinner(f"Generating image for Variant {variant_name}..."):
                        image_data = generate_image(variant.image_prompt, variant_name)
                        if image_data:
                            st.session_state.generated_images[variant_name] = image_data
                        else:
                            st.error(f"Failed to generate image for Variant {variant_name}")
            
            if variant_name in st.session_state.generated_images:
                try:
                    # Display the generated image
                    image_data = st.session_state.generated_images[variant_name]
                    
                    # Convert bytes to PIL Image for display
                    image = Image.open(BytesIO(image_data))
                    st.image(image, width=400, caption=f"Generated by Imagen for Variant {variant_name}")
                    
                    # Show image details
                    st.caption(f"Image size: {image.size[0]}x{image.size[1]} pixels")
                    
                except Exception as e:
                    st.error(f"Error displaying image: {e}")
                    # Remove corrupted image data
                    del st.session_state.generated_images[variant_name]
            
           
        
        with col2:
            # Performance Metrics
            st.markdown("**📊 Simulated Performance:**")
            st.metric("CTR", f"{metrics['ctr']}%")
            st.metric("Engagement", f"{metrics['engagement']}%")
            st.metric("Conversion", f"{metrics['conversion']}%")
            
            # Color Palette
            st.markdown("**🎨 Color Palette:**")
            colors = [variant.color_palette.primary, 
                     variant.color_palette.secondary, 
                     variant.color_palette.accent]
            
            color_cols = st.columns(3)
            labels = ['Primary', 'Secondary', 'Accent']
            for i, (color, label) in enumerate(zip(colors, labels)):
                with color_cols[i]:
                    st.markdown(f"""
                    <div style="background-color: {color}; 
                                height: 50px; 
                                border-radius: 5px; 
                                border: 1px solid #ddd;
                                margin-bottom: 5px;">
                    </div>
                    <small>{label}<br>{color}</small>
                    """, unsafe_allow_html=True)
            
            # Font Recommendation
            st.markdown("**✍️ Font Recommendation:**")
            st.write(variant.font_recommendation)

def main():
    st.title("🎨 GenAI Content Assistant")
    st.markdown("Generate campaign assets with AI-powered A/B testing variants")
    
    # API Configuration
    if not configure_api():
        st.warning("⚠️ Please configure your API settings in the sidebar to continue.")
        st.markdown("""
        **Required Setup:**
        1. **Gemini API Key** - For text generation (Gemini 2.0 Flash)
        2. **Google Cloud Project ID** - For image generation (Imagen models)
        
        **This app uses:**
        - **Gemini 2.0 Flash** for campaign text generation
        - **Imagen 3.0/4.0** for actual image generation
        
        **Make sure your Google Cloud Project has:**
        - Billing enabled
        - Vertex AI API enabled
        - Access to Imagen models
        """)
        st.stop()
    
    # Main Input
    st.header("📝 Creative Brief Input")
    brief = st.text_area(
        "Enter your creative brief:",
        placeholder="Example: Launch promo for fantasy football app targeting Gen Z with meme culture and high-energy visuals.",
        height=100
    )
    
    # Generate Button
    if st.button("🚀 Generate Campaign Variants", type="primary"):
        if not brief:
            st.error("Please enter a creative brief.")
            return
        
        with st.spinner("Generating creative variants..."):
            variants = generate_campaign_variants(brief)
            if variants:
                st.session_state.generated_variants = variants
                st.session_state.generated_images = {}  # Reset images
                st.success("✅ Campaign variants generated successfully!")
            else:
                st.error("Failed to generate variants. Please try again.")
    
    # Display Results
    if st.session_state.generated_variants:
        st.header("🔍 A/B Testing Variants")
        st.markdown("Compare different creative approaches and their simulated performance:")
        
        variants = st.session_state.generated_variants
        
        # Generate simulated metrics for each variant
        metrics_a = simulate_performance_metrics()
        metrics_b = simulate_performance_metrics()
        
        # Display variants in tabs
        tab1, tab2 = st.tabs(["Variant A", "Variant B"])
        
        with tab1:
            display_variant_card(variants.variant_a, "A", metrics_a)
        
        with tab2:
            display_variant_card(variants.variant_b, "B", metrics_b)
        
        
        # Recommendation
        st.header("🏆 AI Recommendation")
        best_metrics = [
            ("A", metrics_a['ctr'] + metrics_a['engagement'] * 0.1 + metrics_a['conversion'] * 2),
            ("B", metrics_b['ctr'] + metrics_b['engagement'] * 0.1 + metrics_b['conversion'] * 2),
            
        ]
        best_variant = max(best_metrics, key=lambda x: x[1])[0]
        
        st.success(f"🎯 **Recommended Variant: {best_variant}** - Shows highest predicted performance based on combined metrics.")
        
        # Export Options
        st.header("📤 Export Campaign Assets")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download Campaign Brief (JSON)"):
                export_data = {
                    "creative_brief": brief,
                    "variants": st.session_state.generated_variants.dict(),
                    "performance_simulation": {
                        "variant_a": metrics_a,
                        "variant_b": metrics_b,
                    },
                    "recommendation": f"Variant {best_variant}"
                }
                
                json_str = json.dumps(export_data, indent=2)
                st.download_button(
                    label="💾 Download JSON",
                    data=json_str,
                    file_name="campaign_assets.json",
                    mime="application/json"
                )
        
        with col2:
            # Export generated images
            if st.session_state.generated_images:
                if st.button("Download Generated Images"):
                    
                    
                    # Create a zip file with all generated images
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for variant_name, image_data in st.session_state.generated_images.items():
                            zip_file.writestr(f"variant_{variant_name}_image.png", image_data)
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="📸 Download Images (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="campaign_images.zip",
                        mime="application/zip"
                    )

if __name__ == "__main__":
    main()