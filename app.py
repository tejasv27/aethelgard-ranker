import streamlit as st
import pandas as pd
import subprocess
import os

# Set up the page UI
st.set_page_config(page_title="Aethelgard Ranker", page_icon="⚙️")
st.title("Aethelgard - Hiring Intelligence Engine")
st.markdown("Upload a candidate dataset (`.jsonl` or `.jsonl.gz`) to run the deterministic ranking pipeline.")

# File uploader for the judges
uploaded_file = st.file_uploader("Upload Candidates File", type=["gz", "jsonl"])

if uploaded_file is not None:
    input_path = f"temp_{uploaded_file.name}"
    output_path = "submission.csv"
    
    # Save the uploaded file to the server
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.info("File uploaded successfully. Initializing Aethelgard ranking engine...")
    
    # Run the rank.py script
    try:
        with st.spinner("Processing candidates and calculating latent metrics..."):
            # This triggers your exact backend script
            subprocess.run(
                ["python", "rank.py", "--candidates", input_path, "--out", output_path], 
                check=True, 
                capture_output=True, 
                text=True
            )
            
        st.success("Ranking complete! Pipeline executed under local constraints.")
        
        # Display the results
        if os.path.exists(output_path):
            df = pd.read_csv(output_path)
            st.subheader("Top 10 Ranked Candidates")
            st.dataframe(df.head(10))
            
            # Create a download button for the final CSV
            with open(output_path, "rb") as file:
                st.download_button(
                    label="Download Full submission.csv",
                    data=file,
                    file_name="submission.csv",
                    mime="text/csv"
                )
        else:
            st.error("Output file was not generated. Check rank.py logic.")
            
    except subprocess.CalledProcessError as e:
        st.error(f"Execution Error: {e.stderr}")
    
    finally:
        # Clean up temporary files
        if os.path.exists(input_path):
            os.remove(input_path)