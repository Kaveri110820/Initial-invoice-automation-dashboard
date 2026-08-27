from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import auth
from ai_extractor import extract_with_ai
from database import (
    add_invoice,
    delete_invoice,
    delete_user,
    find_duplicate,
    get_all_invoices,
    get_all_users,
    get_invoice_by_id,
    initialize_database,
    update_invoice_status,
    update_user_role,
)
from extractor import extract_invoice_data, extract_text_from_pdf

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Invoice Dashboard", page_icon=":receipt:", layout="wide")

initialize_database()

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _render_signin():
    st.markdown("## Sign In")
    with st.form("signin_form", clear_on_submit=False):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        if not email.strip():
            st.error("Email is required.")
        elif not password:
            st.error("Password is required.")
        else:
            ok, err = auth.login(email, password)
            if ok:
                st.session_state["auth_page"] = None
                st.rerun()
            else:
                st.error(err)

    if st.button("Don't have an account? Sign Up"):
        st.session_state["auth_page"] = "signup"
        st.rerun()

    if st.button("Forgot password?"):
        st.session_state["auth_page"] = "forgot"
        st.rerun()


def _render_signup():
    st.markdown("## Sign Up")
    with st.form("signup_form", clear_on_submit=False):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account")

    if submitted:
        if not full_name.strip():
            st.error("Full name is required.")
        elif not email.strip():
            st.error("Email is required.")
        elif not password:
            st.error("Password is required.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            ok, err = auth.create_user(full_name, email, password)
            if ok:
                st.session_state["auth_page"] = "signin"
                st.success("Account created. Please sign in.")
                st.rerun()
            else:
                st.error(err)

    if st.button("Already have an account? Sign In"):
        st.session_state["auth_page"] = "signin"
        st.rerun()


def _render_forgot():
    st.markdown("## Forgot Password")
    st.caption("Enter your account email to receive a password reset token.")
    with st.form("forgot_form", clear_on_submit=False):
        email = st.text_input("Email")
        submitted = st.form_submit_button("Request Reset")
    if submitted:
        if not email.strip():
            st.error("Email is required.")
        else:
            ok, token = auth.request_password_reset(email)
            if ok:
                st.success("A reset token has been generated.")
                st.session_state["reset_email"] = email.strip().lower()
                st.session_state["auth_page"] = "reset"
                st.rerun()
            else:
                st.info(token)

    if st.button("Back to Sign In"):
        st.session_state["auth_page"] = "signin"
        st.rerun()


def _render_reset():
    st.markdown("## Reset Password")
    st.caption("Enter the reset token and choose a new password.")
    with st.form("reset_form", clear_on_submit=False):
        token = st.text_input("Reset Token")
        new_password = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password")
    if submitted:
        if not token.strip():
            st.error("Reset token is required.")
        elif not new_password:
            st.error("New password is required.")
        elif new_password != confirm:
            st.error("Passwords do not match.")
        else:
            email = st.session_state.get("reset_email", "")
            ok, err = auth.reset_password(email, token.strip(), new_password)
            if ok:
                st.success("Password updated. Please sign in with your new password.")
                st.session_state["auth_page"] = "signin"
                st.rerun()
            else:
                st.error(err)

    if st.button("Back to Sign In"):
        st.session_state["auth_page"] = "signin"
        st.rerun()


if not auth.is_logged_in():
    st.set_page_config(page_title="Invoice Dashboard", page_icon=":receipt:", layout="wide")
    st.markdown(
        "<h1 style='text-align:center;'>Invoice Automation Dashboard</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#888;'>Sign in to manage and process invoices.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("")
    page = st.session_state.get("auth_page", "signin")
    if page == "signup":
        _render_signup()
    elif page == "forgot":
        _render_forgot()
    elif page == "reset":
        _render_reset()
    else:
        _render_signin()
    st.stop()

st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h3,
    [data-testid="stSidebar"] label { color: #e0e0e0; }
    [data-testid="stSidebar"] hr { border-color: #333; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 0.5rem;
        padding: 0.75rem 1rem;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 500;
        color: #555;
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .badge-pending  { background: #fff3cd; color: #856404; }
    .badge-approved { background: #d4edda; color: #155724; }
    .badge-rejected { background: #f8d7da; color: #721c24; }

    /* Compact dataframe rows */
    [data-testid="stDataFrame"] row { min-height: 2rem; }
</style>
""",
    unsafe_allow_html=True,
)

PAGES = {
    "Dashboard": "dashboard",
    "Upload Invoice": "upload",
    "Invoice Management": "management",
    "Approval Center": "approval",
    "Analytics": "analytics",
    "User Management": "users",
}

PAGE_ICONS = {
    "Dashboard": "Dashboard",
    "Upload Invoice": "Upload Invoice",
    "Invoice Management": "Invoice Management",
    "Approval Center": "Approval Center",
    "Analytics": "Analytics",
    "User Management": "User Management",
}

STATUS_COLORS = {"Pending": "#FFC107", "Approved": "#4CAF50", "Rejected": "#F44336"}

BADGE_HTML = {
    "Pending": '<span class="badge badge-pending">Pending</span>',
    "Approved": '<span class="badge badge-approved">Approved</span>',
    "Rejected": '<span class="badge badge-rejected">Rejected</span>',
}


def _badge(status: str) -> str:
    return BADGE_HTML.get(status, status)


def _chart_layout(**overrides):
    defaults = dict(margin=dict(t=30, b=30, l=20, r=20), font=dict(size=13))
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Invoice System")
    user = auth.get_current_user()
    if user:
        st.markdown(f"**Signed in as:** {user.get('full_name', user.get('email'))}")
        st.caption(user.get("email", ""))
        st.caption(f"Role: {user.get('role', 'Employee')}")
        if st.button("Logout", use_container_width=True):
            auth.logout()
            st.rerun()
    st.markdown("---")
    visible_keys = [k for k in PAGES if PAGES[k] != "users" or auth.is_admin()]
    selected = st.radio(
        "Navigation",
        visible_keys,
        format_func=lambda x: PAGE_ICONS.get(x, x),
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("AI-Powered Invoice Dashboard")

# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------

def _get_status_counts(invoices: list[dict]) -> dict:
    counts = {"Pending": 0, "Approved": 0, "Rejected": 0}
    for inv in invoices:
        status = inv.get("status", "Pending")
        if status in counts:
            counts[status] += 1
    return counts


def _render_dashboard():
    st.markdown("# Dashboard")
    st.markdown("Overview of all invoices and their status.")
    st.markdown("")

    invoices = get_all_invoices()
    total_value = sum(inv["total_amount"] for inv in invoices)
    counts = _get_status_counts(invoices)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Invoices", f"{len(invoices):,}")
    c2.metric("Pending", f"{counts['Pending']:,}")
    c3.metric("Approved", f"{counts['Approved']:,}")
    c4.metric("Rejected", f"{counts['Rejected']:,}")
    c5.metric("Total Value", f"${total_value:,.2f}")

    st.markdown("")

    if not invoices:
        st.info("No invoices yet. Upload one to get started.")
        return

    left, right = st.columns(2)

    with left:
        st.markdown("#### Invoice Status")
        pie_data = pd.DataFrame(
            [{"Status": k, "Count": v} for k, v in counts.items() if v > 0]
        )
        if not pie_data.empty:
            fig = px.pie(
                pie_data, names="Status", values="Count", color="Status",
                color_discrete_map=STATUS_COLORS,
            )
            fig.update_traces(
                textinfo="label+value",
                textfont_size=13,
                hovertemplate="%{label}<br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            )
            fig.update_layout(**_chart_layout(showlegend=True))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Monthly Invoice Totals")
        df = pd.DataFrame(invoices)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["month"] = df["created_at"].dt.to_period("M").astype(str)
        monthly = df.groupby("month")["total_amount"].sum().reset_index()
        fig = px.bar(
            monthly, x="month", y="total_amount",
            labels={"month": "Month", "total_amount": "Total ($)"},
            color_discrete_sequence=["#1976D2"],
        )
        fig.update_traces(
            hovertemplate="%{x}<br>Total: $%{y:,.2f}<extra></extra>",
            marker_line_width=0,
        )
        fig.update_layout(**_chart_layout(xaxis_tickangle=-45))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Recent Invoices")
    display_cols = ["id", "invoice_number", "vendor_name", "total_amount", "status", "created_at"]
    df_display = pd.DataFrame(invoices)[display_cols].head(10)
    df_display.columns = ["ID", "Invoice #", "Vendor", "Amount", "Status", "Uploaded"]
    st.dataframe(
        df_display, use_container_width=True, hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Amount": st.column_config.NumberColumn(format="$%.2f"),
        },
    )

# ---------------------------------------------------------------------------
# Page: Upload Invoice
# ---------------------------------------------------------------------------

def _render_upload():
    st.markdown("# Upload Invoice")
    st.markdown("Upload a PDF invoice to extract and review its data before saving.")
    st.markdown("")

    uploaded_files = st.file_uploader(
        "Choose PDF invoices", type=["pdf"], accept_multiple_files=True,
        help="Accepted format: PDF",
    )

    if not uploaded_files:
        st.info("Select one or more PDF files to upload and extract data from.")
        return

    for uploaded in uploaded_files:
        with st.container(border=True):
            st.markdown(f"#### {uploaded.name}")

            safe_name = Path(uploaded.name).name
            save_path = UPLOAD_DIR / safe_name
            save_path.write_bytes(uploaded.getvalue())

            raw_text = extract_text_from_pdf(str(save_path))
            extracted = extract_with_ai(raw_text)
            extraction_method = "AI"

            if extracted is None:
                extracted = extract_invoice_data(raw_text)
                extraction_method = "Rule-based"

            st.caption(f"Extraction method: **{extraction_method}**")

            with st.form(key=f"form_{uploaded.name}"):
                col1, col2 = st.columns(2)
                with col1:
                    vendor_name = st.text_input("Vendor Name", extracted["vendor_name"])
                    invoice_number = st.text_input("Invoice Number", extracted["invoice_number"])
                    invoice_date = st.text_input("Invoice Date", extracted["invoice_date"])
                    due_date = st.text_input("Due Date", extracted["due_date"])
                with col2:
                    subtotal = st.number_input("Subtotal", value=extracted["subtotal"], format="%.2f")
                    tax = st.number_input("Tax", value=extracted["tax"], format="%.2f")
                    total_amount = st.number_input("Total Amount", value=extracted["total_amount"], format="%.2f")
                    currency = st.text_input("Currency", "USD")

                submitted = st.form_submit_button("Save Invoice", type="primary")

                if submitted:
                    if not vendor_name:
                        st.error("Vendor name is required.")
                        return

                    existing = find_duplicate(invoice_number, vendor_name, total_amount)
                    if existing:
                        st.warning(
                            f"Duplicate detected — matches invoice #{existing['id']} "
                            f"({existing['invoice_number']}) with the same amount."
                        )
                        return

                    inv_id = add_invoice({
                        "vendor_name": vendor_name,
                        "invoice_number": invoice_number,
                        "invoice_date": invoice_date,
                        "due_date": due_date,
                        "subtotal": subtotal,
                        "tax": tax,
                        "total_amount": total_amount,
                        "currency": currency,
                        "file_name": uploaded.name,
                        "extracted_text": raw_text,
                    })
                    st.success(f"Invoice saved with ID **{inv_id}**")

            with st.expander("Extracted PDF Text"):
                st.code(raw_text, language=None)

# ---------------------------------------------------------------------------
# Page: Invoice Management
# ---------------------------------------------------------------------------

def _render_management():
    st.markdown("# Invoice Management")
    st.markdown("Search, filter, and manage all invoices.")
    st.markdown("")

    invoices = get_all_invoices()
    if not invoices:
        st.info("No invoices found.")
        return

    df_all = pd.DataFrame(invoices)

    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([1, 1, 2, 2])
        with f1:
            status_filter = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"])
        with f2:
            vendor_list = ["All"] + sorted(df_all["vendor_name"].dropna().unique().tolist())
            vendor_filter = st.selectbox("Vendor", vendor_list)
        with f3:
            date_from = st.date_input("From", value=None)
        with f4:
            date_to = st.date_input("To", value=None)

        search = st.text_input("Search", placeholder="Invoice number or vendor name...")

    filtered = invoices
    if status_filter != "All":
        filtered = [i for i in filtered if i["status"] == status_filter]
    if vendor_filter != "All":
        filtered = [i for i in filtered if i["vendor_name"] == vendor_filter]
    if search:
        q = search.lower()
        filtered = [
            i for i in filtered
            if q in (i["invoice_number"] or "").lower()
            or q in (i["vendor_name"] or "").lower()
        ]
    if date_from:
        d = date_from.strftime("%Y-%m-%d")
        filtered = [i for i in filtered if (i["invoice_date"] or "") >= d]
    if date_to:
        d = date_to.strftime("%Y-%m-%d")
        filtered = [i for i in filtered if (i["invoice_date"] or "") <= d]

    st.caption(f"**{len(filtered)}** invoice(s) shown")

    if not filtered:
        st.info("No invoices match the current filters.")
        return

    display_rows = []
    for inv in filtered:
        display_rows.append({
            "ID": inv["id"],
            "Invoice #": inv["invoice_number"],
            "Vendor": inv["vendor_name"],
            "Invoice Date": inv["invoice_date"],
            "Due Date": inv["due_date"],
            "Amount": inv["total_amount"],
            "Status": inv["status"],
            "Created": inv["created_at"],
        })

    df_display = pd.DataFrame(display_rows)
    st.dataframe(
        df_display, use_container_width=True, hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Amount": st.column_config.NumberColumn(format="$%.2f"),
            "Invoice Date": st.column_config.TextColumn(width="medium"),
            "Due Date": st.column_config.TextColumn(width="medium"),
            "Status": st.column_config.TextColumn(width="medium"),
        },
    )

    st.markdown("---")
    st.markdown("#### Invoice Details")

    inv_ids = [inv["id"] for inv in filtered]
    selected_id = st.selectbox(
        "Select an invoice to view details",
        inv_ids,
        format_func=lambda x: (
            f"#{x} — "
            f"{next(i['vendor_name'] for i in filtered if i['id'] == x)} — "
            f"${next(i['total_amount'] for i in filtered if i['id'] == x):,.2f}"
        ),
    )

    inv = get_invoice_by_id(selected_id)
    if not inv:
        st.error("Invoice not found.")
        return

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Invoice #:** {inv['invoice_number']}")
            st.markdown(f"**Vendor:** {inv['vendor_name']}")
            st.markdown(f"**Invoice Date:** {inv['invoice_date']}")
            st.markdown(f"**Due Date:** {inv['due_date']}")
            st.markdown(f"**Currency:** {inv['currency']}")
            st.markdown(f"**Status:** {_badge(inv['status'])}", unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Subtotal:** ${inv['subtotal']:,.2f}")
            st.markdown(f"**Tax:** ${inv['tax']:,.2f}")
            st.markdown(f"**Total:** ${inv['total_amount']:,.2f}")
            st.markdown(f"**File:** `{inv['file_name']}`")
            st.markdown(f"**Uploaded:** {inv['created_at']}")
            st.markdown(f"**Updated:** {inv['updated_at']}")

    with st.expander("Extracted PDF Text"):
        st.code(inv["extracted_text"], language=None)

    st.markdown("---")
    if st.button("Delete this invoice", type="secondary"):
        delete_invoice(inv["id"])
        st.success(f"Invoice #{inv['id']} deleted.")
        st.rerun()

# ---------------------------------------------------------------------------
# Page: Approval Center
# ---------------------------------------------------------------------------

def _render_approval():
    st.markdown("# Approval Center")
    st.markdown("Review and process pending invoices.")
    st.markdown("")

    pending = get_all_invoices("Pending")
    if not pending:
        st.success("No invoices pending review.")
        return

    st.caption(f"**{len(pending)}** invoice(s) awaiting approval")

    inv_ids = [inv["id"] for inv in pending]
    selected_id = st.selectbox(
        "Select an invoice to review",
        inv_ids,
        format_func=lambda x: (
            f"#{x} — "
            f"{next(i['vendor_name'] for i in pending if i['id'] == x)} — "
            f"${next(i['total_amount'] for i in pending if i['id'] == x):,.2f}"
        ),
    )

    inv = get_invoice_by_id(selected_id)
    if not inv:
        st.error("Invoice not found.")
        return

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Invoice #:** {inv['invoice_number']}")
            st.markdown(f"**Vendor:** {inv['vendor_name']}")
            st.markdown(f"**Invoice Date:** {inv['invoice_date']}")
            st.markdown(f"**Due Date:** {inv['due_date']}")
            st.markdown(f"**Status:** {_badge(inv['status'])}", unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Subtotal:** ${inv['subtotal']:,.2f}")
            st.markdown(f"**Tax:** ${inv['tax']:,.2f}")
            st.markdown(f"**Total:** ${inv['total_amount']:,.2f}")
            st.markdown(f"**File:** `{inv['file_name']}`")
            st.markdown(f"**Uploaded:** {inv['created_at']}")

    with st.expander("Extracted PDF Text"):
        st.code(inv["extracted_text"], language=None)

    st.markdown("---")

    if not auth.is_admin():
        st.info("You have read-only access to the Approval Center. Only an Administrator can approve or reject invoices.")
        return

    a1, a2 = st.columns(2)

    with a1:
        if st.button("Approve", type="primary", key=f"approve_{inv['id']}"):
            with st.expander("Confirm Approval", expanded=True):
                st.warning(f"Approve invoice **#{inv['id']}** from **{inv['vendor_name']}**?")
                co1, co2, _ = st.columns([1, 1, 1])
                with co1:
                    if st.button("Yes, Approve", type="primary", key=f"confirm_app_{inv['id']}"):
                        update_invoice_status(inv["id"], "Approved")
                        st.success(f"Invoice #{inv['id']} approved.")
                        st.rerun()
                with co2:
                    if st.button("Cancel", key=f"cancel_app_{inv['id']}"):
                        st.rerun()

    with a2:
        if st.button("Reject", key=f"reject_{inv['id']}"):
            with st.expander("Confirm Rejection", expanded=True):
                st.warning(f"Reject invoice **#{inv['id']}** from **{inv['vendor_name']}**?")
                co1, co2, _ = st.columns([1, 1, 1])
                with co1:
                    if st.button("Yes, Reject", key=f"confirm_rej_{inv['id']}"):
                        update_invoice_status(inv["id"], "Rejected")
                        st.success(f"Invoice #{inv['id']} rejected.")
                        st.rerun()
                with co2:
                    if st.button("Cancel", key=f"cancel_rej_{inv['id']}"):
                        st.rerun()

# ---------------------------------------------------------------------------
# Page: Analytics
# ---------------------------------------------------------------------------

def _render_analytics():
    st.markdown("# Analytics")
    st.markdown("Visual breakdown of invoice data.")
    st.markdown("")

    invoices = get_all_invoices()
    if not invoices:
        st.info("No data available for analytics.")
        return

    df = pd.DataFrame(invoices)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["month"] = df["created_at"].dt.to_period("M").astype(str)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Invoice Count by Status")
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_bar = px.bar(
            status_counts, x="Status", y="Count", color="Status",
            color_discrete_map=STATUS_COLORS, text="Count",
        )
        fig_bar.update_traces(
            textposition="outside",
            hovertemplate="%{x}: %{y}<extra></extra>",
            marker_line_width=0,
        )
        fig_bar.update_layout(**_chart_layout(showlegend=False))
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.markdown("#### Pending vs Approved vs Rejected")
        fig_donut = px.pie(
            status_counts, names="Status", values="Count", color="Status",
            color_discrete_map=STATUS_COLORS, hole=0.45,
        )
        fig_donut.update_traces(
            textinfo="label+value",
            hovertemplate="%{label}<br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        )
        fig_donut.update_layout(**_chart_layout())
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("#### Total Invoice Amount by Month")
    monthly = df.groupby("month").agg(
        total=("total_amount", "sum"),
        count=("id", "count"),
    ).reset_index()
    fig_monthly = px.bar(
        monthly, x="month", y="total",
        labels={"month": "Month", "total": "Total ($)"},
        color_discrete_sequence=["#1976D2"],
        text="total",
        hover_data={"count": True, "total": ":$,.2f"},
    )
    fig_monthly.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        hovertemplate="%{x}<br>Total: $%{y:,.2f}<br>Invoices: %{customdata[0]}<extra></extra>",
        marker_line_width=0,
    )
    fig_monthly.update_layout(**_chart_layout(xaxis_tickangle=-45))
    st.plotly_chart(fig_monthly, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown("#### Invoice Amount by Vendor")
        vendor_totals = (
            df.groupby("vendor_name")["total_amount"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        fig_vendor = px.bar(
            vendor_totals, x="total_amount", y="vendor_name", orientation="h",
            labels={"total_amount": "Total ($)", "vendor_name": ""},
            color_discrete_sequence=["#7B1FA2"],
        )
        fig_vendor.update_traces(
            hovertemplate="%{y}<br>Total: $%{x:,.2f}<extra></extra>",
            marker_line_width=0,
        )
        fig_vendor.update_layout(**_chart_layout())
        st.plotly_chart(fig_vendor, use_container_width=True)

    with c4:
        st.markdown("#### Top Vendors by Invoice Value")
        top_n = min(10, len(vendor_totals))
        top_vendors = vendor_totals.tail(top_n)
        fig_top = px.bar(
            top_vendors, x="total_amount", y="vendor_name", orientation="h",
            labels={"total_amount": "Total ($)", "vendor_name": ""},
            color="total_amount", color_continuous_scale="Viridis",
        )
        fig_top.update_traces(
            hovertemplate="%{y}<br>Total: $%{x:,.2f}<extra></extra>",
            marker_line_width=0,
        )
        fig_top.update_layout(**_chart_layout(coloraxis_showscale=False))
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Invoices", f"{len(df):,}")
    s2.metric("Total Value", f"${df['total_amount'].sum():,.2f}")
    s3.metric("Average Invoice", f"${df['total_amount'].mean():,.2f}")
    s4.metric("Unique Vendors", f"{df['vendor_name'].nunique():,}")

    st.markdown("#### All Invoices")
    display_cols = ["id", "invoice_number", "vendor_name", "total_amount", "tax", "status", "created_at"]
    st.dataframe(
        df[display_cols], use_container_width=True, hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "tax": st.column_config.NumberColumn("Tax", format="$%.2f"),
            "status": st.column_config.TextColumn("Status"),
            "created_at": st.column_config.TextColumn("Created"),
        },
    )

# ---------------------------------------------------------------------------
# Page: User Management (Admin only)
# ---------------------------------------------------------------------------

def _render_users():
    if not auth.is_admin():
        st.error("You do not have permission to access User Management.")
        return
    st.markdown("# User Management")
    st.markdown("Manage user accounts and roles.")
    st.markdown("")

    users = get_all_users()
    if not users:
        st.info("No users found.")
        return

    df = pd.DataFrame(users)
    df["created_at"] = df["created_at"].astype(str)
    st.dataframe(
        df[["id", "full_name", "email", "role", "created_at"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "full_name": st.column_config.TextColumn("Full Name"),
            "email": st.column_config.TextColumn("Email"),
            "role": st.column_config.TextColumn("Role"),
            "created_at": st.column_config.TextColumn("Created"),
        },
    )

    st.markdown("#### Change Role")
    cur = auth.get_current_user()
    target = st.selectbox(
        "Select user",
        users,
        format_func=lambda u: f"{u['full_name']} ({u['email']}) — {u['role']}",
        key="role_target",
    )
    new_role = st.selectbox("New role", list(auth.ROLES), key="role_new")
    if st.button("Update Role", key="update_role"):
        if target["id"] == cur.get("id"):
            st.error("You cannot change your own role.")
        elif new_role == target["role"]:
            st.info("Role is already set to that value.")
        else:
            update_user_role(target["id"], new_role)
            st.success(f"Role for {target['email']} updated to {new_role}.")
            st.rerun()

    st.markdown("#### Remove User")
    del_target = st.selectbox(
        "Select user to remove",
        users,
        format_func=lambda u: f"{u['full_name']} ({u['email']})",
        key="del_target",
    )
    if st.button("Delete User", type="secondary", key="delete_user"):
        if del_target["id"] == cur.get("id"):
            st.error("You cannot delete your own account.")
        else:
            delete_user(del_target["id"])
            st.success(f"User {del_target['email']} deleted.")
            st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

page_map = {
    "dashboard": _render_dashboard,
    "upload": _render_upload,
    "management": _render_management,
    "approval": _render_approval,
    "analytics": _render_analytics,
    "users": _render_users,
}

page_map[PAGES[selected]]()
