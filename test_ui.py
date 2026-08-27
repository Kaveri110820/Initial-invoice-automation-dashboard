import streamlit as st

st.set_page_config(page_title="Test", page_icon=":receipt:", layout="wide")

# Test column_config with width parameter
try:
    df_data = [{"ID": 1, "Status": "Pending", "Amount": 100.0}]
    st.dataframe(
        df_data,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
        },
    )
    st.success("column_config with width: OK")
except Exception as e:
    st.error(f"column_config with width FAILED: {e}")
    import traceback
    st.code(traceback.format_exc())
