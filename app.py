import streamlit as st
import config
from src.synthesiser import generate_insights

st.set_page_config(page_title="Editorial Data Vault", page_icon="📊", layout="wide")

st.title("Editorial Data Vault")
st.markdown("Generate strategic insights by combining editorial expertise, brand research, audience data, and market trends.")

# Check for API key
if not config.OPENAI_API_KEY:
    st.error("Missing `OPENAI_API_KEY`. Add it to your `.env` file and restart the app.")
    st.stop()

# Inputs
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("Topic", placeholder="e.g. gut health, skincare, sustainable fashion")
with col2:
    advertiser = st.text_input("Advertiser", placeholder="e.g. Yakult, The Ordinary, Patagonia")

include_trends = st.checkbox("Include Google Trends data", value=True,
                              help="Pulls live data from Google Trends. Disable if it's slow or failing.")

# Generate
if st.button("Generate Insights", type="primary", disabled=not (topic and advertiser)):
    with st.spinner("Gathering editorial insights, brand research, audience data, and trends..."):
        try:
            result = generate_insights(
                topic=topic,
                advertiser=advertiser,
                include_google_trends=include_trends,
            )

            st.markdown("---")
            st.markdown(result["content"])

            # Sources panel
            if result["sources"]:
                with st.expander("Sources & Attribution"):
                    for source in result["sources"]:
                        st.markdown(
                            f"- **{source['editor']}**, {source['publication']} "
                            f"({source['date']}) — *{source['vertical']}*: {source['topics']}"
                        )

            # Advertiser Research panel
            if result.get("research_skills"):
                with st.expander("Advertiser Research"):
                    for skill_result in result["research_skills"]:
                        st.subheader(skill_result["skill_name"])
                        if skill_result.get("error"):
                            st.warning(f"Error: {skill_result['error']}")
                        st.markdown(skill_result["processed_summary"])

                        # Raw search snippets
                        if skill_result["raw_results"]:
                            with st.expander(f"Raw search results ({len(skill_result['raw_results'])} snippets)"):
                                for r in skill_result["raw_results"]:
                                    href = r.get("href", "")
                                    title = r.get("title", "Untitled")
                                    if href:
                                        st.markdown(f"- [{title}]({href}): {r['body']}")
                                    else:
                                        st.markdown(f"- **{title}**: {r['body']}")

            # Audience Data panel
            if result.get("audience_timing"):
                with st.expander("Audience Data"):
                    st.text(result["audience_timing"])

            # Google Trends panel
            if result.get("google_trends"):
                with st.expander("Google Trends"):
                    st.text(result["google_trends"])

        except Exception as e:
            st.error(f"An error occurred: {e}")

elif not topic or not advertiser:
    st.info("Enter a topic and advertiser to get started.")
