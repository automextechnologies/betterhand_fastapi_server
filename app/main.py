import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.infrastructure.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.routers.auth import router as auth_router
from app.api.routers.ward import router as ward_router
from app.api.routers.donation import router as donation_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    await connect_to_mongo()
    yield
    # Shutdown actions
    await close_mongo_connection()

app = FastAPI(
    title="Betterhand API Backend",
    description="FastAPI migration of the Betterhand backend with Clean Architecture and MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
# Allowing all origins and IPs for public API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# API Route Registrations
app.include_router(auth_router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ward_router, prefix="/api/ward", tags=["Ward"])
app.include_router(donation_router, prefix="/api/donation", tags=["Donation"])


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Betterhand API",
        "version": "1.0.0"
    }


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admi", response_class=HTMLResponse)
async def admin_dashboard():
    try:
        from app.infrastructure.database.mongodb import db
        
        # Bulk query from collections to prevent N+1 queries
        users = await db.db.users.find({}).to_list(length=10000)
        hospitals = await db.db.hospital_profiles.find({}).to_list(length=10000)
        donors = await db.db.donor_profiles.find({}).to_list(length=10000)
        ward_members = await db.db.ward_members.find({}).to_list(length=10000)
        wards = await db.db.wards.find({}).to_list(length=10000)
    except Exception as e:
        logger.error(f"Database error in admin dashboard: {e}")
        return HTMLResponse(
            content=f"""
            <html>
                <head>
                    <title>BetterHand Admin | Connection Error</title>
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="bg-slate-50 flex items-center justify-center min-h-screen">
                    <div class="bg-white p-8 rounded-xl shadow-md border border-slate-200 max-w-md text-center">
                        <div class="text-rose-500 mb-4">
                            <svg class="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                            </svg>
                        </div>
                        <h2 class="text-xl font-bold text-slate-800 mb-2">Database Connection Failure</h2>
                        <p class="text-slate-500 text-sm mb-6">Could not connect to MongoDB. Verify your database connection string or IP whitelist settings.</p>
                        <div class="bg-slate-50 p-3 rounded text-left text-xs font-mono text-slate-600 overflow-x-auto">{str(e)}</div>
                    </div>
                </body>
            </html>
            """,
            status_code=500
        )
        
    # Map users and wards by string ID
    user_map = {str(u["_id"]): u for u in users}
    ward_map = {str(w["_id"]): w for w in wards}
    
    # Counters
    total_hospitals = len(hospitals)
    total_donors = len(donors)
    total_ward_members = len(ward_members)
    total_users = len(users)
    
    push_enabled_count = sum(1 for u in users if u.get("fcm_token"))
    push_percentage = round((push_enabled_count / total_users * 100), 1) if total_users > 0 else 0.0

    # Build Hospital Rows
    hospital_rows = ""
    for i, h in enumerate(hospitals, 1):
        uid = str(h.get("user_id", ""))
        u = user_map.get(uid, {})
        email = u.get("email", "N/A")
        
        v_badge = '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Verified</span>' if h.get("is_verified") else '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Unverified</span>'
        
        hospital_rows += f"""
        <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100 search-row" data-search="{h.get('name', '')} {email} {h.get('phone', '')} {h.get('district', '')}">
            <td class="px-6 py-4 text-sm text-slate-500 font-medium">{i}</td>
            <td class="px-6 py-4 text-sm font-semibold text-slate-900">{h.get('name', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{email}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{h.get('phone', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{h.get('registration_number', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{h.get('city', 'N/A')}, {h.get('district', 'N/A')}</td>
            <td class="px-6 py-4 text-sm">{v_badge}</td>
        </tr>
        """

    # Build Donor Rows
    donor_rows = ""
    for i, d in enumerate(donors, 1):
        uid = str(d.get("user_id", ""))
        u = user_map.get(uid, {})
        email = u.get("email", "N/A")
        fcm = u.get("fcm_token")
        
        push_badge = '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Enabled</span>' if fcm else '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-500">Disabled</span>'
        
        donor_rows += f"""
        <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100 search-row" data-search="{d.get('full_name', '')} {email} {d.get('blood_group', '')} {d.get('district', '')}">
            <td class="px-6 py-4 text-sm text-slate-500 font-medium">{i}</td>
            <td class="px-6 py-4 text-sm font-semibold text-slate-900">{d.get('full_name', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-rose-600 font-bold text-center">{d.get('blood_group', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600 text-center">{d.get('age', 'N/A')} ({d.get('gender', 'N/A')})</td>
            <td class="px-6 py-4 text-sm text-slate-600">{d.get('phone', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{d.get('district', 'N/A')}, {d.get('local_body_name', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-center">{push_badge}</td>
        </tr>
        """

    # Build Ward Member Rows
    ward_member_rows = ""
    for i, wm in enumerate(ward_members, 1):
        uid = str(wm.get("user_id", ""))
        u = user_map.get(uid, {})
        email = u.get("email", "N/A")
        fcm = u.get("fcm_token")
        wid = str(wm.get("ward_id", ""))
        w_info = ward_map.get(wid, {})
        ward_display = f"Ward {w_info.get('ward_number', 'N/A')} ({w_info.get('local_body_name', 'N/A')})" if w_info else "N/A"
        
        v_badge = '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Verified</span>' if wm.get("is_verified") else '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Unverified</span>'
        push_badge = '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Enabled</span>' if fcm else '<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-500">Disabled</span>'
        
        ward_member_rows += f"""
        <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100 search-row" data-search="{wm.get('full_name', '')} {email} {wm.get('phone', '')} {ward_display}">
            <td class="px-6 py-4 text-sm text-slate-500 font-medium">{i}</td>
            <td class="px-6 py-4 text-sm font-semibold text-slate-900">{wm.get('full_name', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{email}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{wm.get('phone', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{wm.get('designation', 'N/A')}</td>
            <td class="px-6 py-4 text-sm text-slate-600">{ward_display}</td>
            <td class="px-6 py-4 text-sm">{v_badge}</td>
            <td class="px-6 py-4 text-sm text-center">{push_badge}</td>
        </tr>
        """

    # Handle Empty Lists
    if not hospital_rows:
        hospital_rows = '<tr><td colspan="7" class="px-6 py-8 text-center text-sm text-slate-400">No registered hospitals found.</td></tr>'
    if not donor_rows:
        donor_rows = '<tr><td colspan="7" class="px-6 py-8 text-center text-sm text-slate-400">No registered donors found.</td></tr>'
    if not ward_member_rows:
        ward_member_rows = '<tr><td colspan="8" class="px-6 py-8 text-center text-sm text-slate-400">No registered ward members found.</td></tr>'

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BetterHand | Admin Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
            }}
        </style>
    </head>
    <body class="bg-slate-50 min-h-screen text-slate-800 flex flex-col">
        <!-- Header -->
        <header class="bg-slate-900 text-white py-6 shadow-md">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <h1 class="text-2xl font-bold tracking-tight flex items-center gap-2 text-rose-500">
                        <span class="text-white">BetterHand</span> Admin
                    </h1>
                    <p class="text-slate-400 text-sm mt-1">Real-time overview of registered participants and system telemetry</p>
                </div>
                <div class="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 w-fit">
                    <span class="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-xs text-slate-300 font-semibold uppercase tracking-wider">Production Server Online</span>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
            <!-- Stats Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <!-- Total Hospitals Card -->
                <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6 hover:shadow-md transition-shadow">
                    <div class="flex items-center justify-between mb-4">
                        <span class="text-sm font-medium text-slate-500 uppercase tracking-wider">Hospitals</span>
                        <div class="p-2 bg-blue-50 text-blue-600 rounded-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
                            </svg>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-900">{total_hospitals}</h3>
                    <p class="text-xs text-slate-400 mt-2">Registered clinical centers</p>
                </div>

                <!-- Total Donors Card -->
                <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6 hover:shadow-md transition-shadow">
                    <div class="flex items-center justify-between mb-4">
                        <span class="text-sm font-medium text-slate-500 uppercase tracking-wider">Donors</span>
                        <div class="p-2 bg-rose-50 text-rose-600 rounded-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                            </svg>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-900">{total_donors}</h3>
                    <p class="text-xs text-slate-400 mt-2">Verified volunteer base</p>
                </div>

                <!-- Total Ward Members Card -->
                <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6 hover:shadow-md transition-shadow">
                    <div class="flex items-center justify-between mb-4">
                        <span class="text-sm font-medium text-slate-500 uppercase tracking-wider">Ward Coordinators</span>
                        <div class="p-2 bg-amber-50 text-amber-600 rounded-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                            </svg>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-900">{total_ward_members}</h3>
                    <p class="text-xs text-slate-400 mt-2">Local network representatives</p>
                </div>

                <!-- Push Opt-In Card -->
                <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6 hover:shadow-md transition-shadow">
                    <div class="flex items-center justify-between mb-4">
                        <span class="text-sm font-medium text-slate-500 uppercase tracking-wider">Push Notifications</span>
                        <div class="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                            </svg>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-900">{push_enabled_count} <span class="text-lg font-medium text-slate-400">/ {total_users}</span></h3>
                    <p class="text-xs text-emerald-600 font-semibold mt-2">{push_percentage}% opt-in rate</p>
                </div>
            </div>

            <!-- Controls (Search + Tabs) -->
            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6 bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <!-- Search -->
                <div class="relative flex-1 max-w-md">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-400">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.637 10.637z" />
                        </svg>
                    </span>
                    <input type="text" id="searchInput" oninput="filterTable()" placeholder="Search names, emails, locations..." class="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-colors">
                </div>
                
                <!-- Tabs -->
                <div class="flex border-b border-slate-100 p-1 bg-slate-50 rounded-lg border">
                    <button onclick="switchTab('hospitals')" id="tab-hospitals" class="tab-btn px-4 py-1.5 text-sm font-semibold rounded-md transition-colors bg-white shadow text-rose-600">
                        Hospitals ({total_hospitals})
                    </button>
                    <button onclick="switchTab('donors')" id="tab-donors" class="tab-btn px-4 py-1.5 text-sm font-semibold rounded-md transition-colors text-slate-600 hover:text-slate-900">
                        Donors ({total_donors})
                    </button>
                    <button onclick="switchTab('ward_members')" id="tab-ward_members" class="tab-btn px-4 py-1.5 text-sm font-semibold rounded-md transition-colors text-slate-600 hover:text-slate-900">
                        Ward Members ({total_ward_members})
                    </button>
                </div>
            </div>

            <!-- Tables container -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden">
                <!-- Hospitals Table -->
                <div id="table-hospitals" class="tab-content block overflow-x-auto">
                    <table class="min-w-full divide-y divide-slate-200">
                        <thead class="bg-slate-50">
                            <tr>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-16">#</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Hospital Name</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Email Address</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Phone</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Reg No.</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Location</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200">
                            {hospital_rows}
                        </tbody>
                    </table>
                </div>

                <!-- Donors Table -->
                <div id="table-donors" class="tab-content hidden overflow-x-auto">
                    <table class="min-w-full divide-y divide-slate-200">
                        <thead class="bg-slate-50">
                            <tr>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-16">#</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Full Name</th>
                                <th scope="col" class="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider w-32">Blood Group</th>
                                <th scope="col" class="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider w-28">Demographics</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Phone</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Location / District</th>
                                <th scope="col" class="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider w-32">Push Notification</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200">
                            {donor_rows}
                        </tbody>
                    </table>
                </div>

                <!-- Ward Members Table -->
                <div id="table-ward_members" class="tab-content hidden overflow-x-auto">
                    <table class="min-w-full divide-y divide-slate-200">
                        <thead class="bg-slate-50">
                            <tr>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-16">#</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Full Name</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Email Address</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Phone</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Designation</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Assigned Ward</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Verification</th>
                                <th scope="col" class="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider w-32">Push Notification</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200">
                            {ward_member_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="bg-slate-900 border-t border-slate-800 text-slate-400 py-6 text-center text-sm">
            <div class="max-w-7xl mx-auto px-4">
                &copy; 2026 BetterHand. All administrative operations are logged securely.
            </div>
        </footer>

        <!-- Interactive Logic -->
        <script>
            let currentTab = 'hospitals';

            function switchTab(tabId) {{
                currentTab = tabId;
                
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
                
                // Show selected tab content
                document.getElementById('table-' + tabId).classList.remove('hidden');
                
                // Reset tab button states
                document.querySelectorAll('.tab-btn').forEach(btn => {{
                    btn.classList.remove('bg-white', 'shadow', 'text-rose-600');
                    btn.classList.add('text-slate-600', 'hover:text-slate-900');
                }});
                
                // Set active button state
                const activeBtn = document.getElementById('tab-' + tabId);
                activeBtn.classList.remove('text-slate-600', 'hover:text-slate-900');
                activeBtn.classList.add('bg-white', 'shadow', 'text-rose-600');
                
                // Re-apply search filter for new active tab
                filterTable();
            }}

            function filterTable() {{
                const query = document.getElementById('searchInput').value.toLowerCase().trim();
                const activeTable = document.getElementById('table-' + currentTab);
                const rows = activeTable.querySelectorAll('.search-row');
                
                rows.forEach(row => {{
                    const searchContent = row.getAttribute('data-search').toLowerCase();
                    if (searchContent.includes(query)) {{
                        row.classList.remove('hidden');
                    }} else {{
                        row.classList.add('hidden');
                    }}
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
