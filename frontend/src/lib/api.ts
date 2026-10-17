const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export function getImageUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("/")) {
    return `${API_URL}${path}`;
  }
  return `${API_URL}/${path}`;
}

function dispatchAuthStateChange() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("auth-state-changed"));
  }
}

export function getStoredAuthUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("auth_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(localStorage.getItem("auth_token"));
}

export function setAuthSession(token: string, user: AuthUser): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("auth_token", token);
  localStorage.setItem("auth_user", JSON.stringify(user));
  dispatchAuthStateChange();
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
  dispatchAuthStateChange();
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Property {
  id: string;
  title: string;
  address: string;
  district: string;
  khoroo: string;
  price: number;
  area: number;
  rooms: number;
  floor: number;
  totalFloors: number;
  builtYear: number;
  buildingType: string;
  developer: string;
  permitStatus: "valid" | "invalid" | "unknown";
  riskLevel: "low" | "medium" | "high";
  lat: number;
  lng: number;
  description: string;
}

export interface RiskItem {
  type: string;
  label: string;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
  source?: string;
  updatedAt?: string;
}

export interface RiskAssessment {
  propertyId: string;
  score: number;
  level: "low" | "medium" | "high";
  items: RiskItem[];
  updatedAt: string;
}

export interface PriceComparable {
  title: string;
  price: number;
  area: number;
  district: string;
}

export interface PriceAnalysis {
  propertyId: string;
  districtAvgPerM2: number;
  cityAvgPerM2: number;
  comparables: PriceComparable[];
  updatedAt: string;
}

export interface BlacklistEntry {
  companyName: string;
  reason: string;
  source: string;
  details?: string;
  listedDate: string;
}

export interface BlacklistResult {
  found: boolean;
  query: string;
  entries?: BlacklistEntry[];
  updatedAt: string;
}

export interface Contract {
  id: string;
  ownerName: string;
  ownerEmail: string;
  tenantName: string;
  tenantEmail: string;
  address: string;
  area: number;
  rooms: number;
  monthlyRent: string;
  deposit: string;
  startDate: string;
  endDate: string;
  ownerSigned: boolean;
  tenantSigned: boolean;
  createdAt: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isBrowser = typeof window !== "undefined";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers instanceof Headers ? Object.fromEntries(options.headers.entries()) : (options.headers as Record<string, string> | undefined) ?? {}),
  };

  if (!headers.Authorization && isBrowser) {
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      throw new Error("API таталт 15 секунд хүртэл хүлээлээ. Сервер хариу өгөхгүй байна.");
    }
    throw new Error("Сервертэй холболт алдаатай байна. Дахин оролдоно уу.");
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("Нэвтрэх шаардлагатай эсвэл сесс хүчингүй болсон байна");
    }
    const body = await res.text();
    throw new Error(`API алдаа (${res.status}): ${body || res.statusText}`);
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/pdf")) {
    return (await res.blob()) as unknown as T;
  }

  if (!contentType.includes("application/json")) {
    return {} as T;
  }

  return res.json();
}

// ─── Properties ──────────────────────────────────────────────────────────────

export function searchProperties(params: {
  q?: string;
  district?: string;
  risk?: string;
  minPrice?: number;
  maxPrice?: number;
}): Promise<Property[]> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.district) qs.set("district", params.district);
  if (params.risk) qs.set("risk", params.risk);
  if (params.minPrice != null) qs.set("min_price", String(params.minPrice));
  if (params.maxPrice != null) qs.set("max_price", String(params.maxPrice));
  return apiFetch(`/properties?${qs}`);
}

export function getProperty(id: string): Promise<Property> {
  return apiFetch(`/properties/${id}`);
}

// ─── Risk ─────────────────────────────────────────────────────────────────────

export function getRiskAssessment(propertyId: string): Promise<RiskAssessment> {
  return apiFetch(`/risk/${propertyId}`);
}

export function getRiskZones(layer: string = "flood_risk_zones", district?: string): Promise<any> {
  const qs = district ? `?district=${encodeURIComponent(district)}` : "";
  return apiFetch(`/risk/zones/${layer}${qs}`);
}

// ─── Price ───────────────────────────────────────────────────────────────────

export function getPriceAnalysis(propertyId: string): Promise<PriceAnalysis> {
  return apiFetch(`/price/${propertyId}`);
}

// ─── Blacklist ────────────────────────────────────────────────────────────────

export function checkBlacklist(query: string): Promise<BlacklistResult> {
  return apiFetch(`/blacklist/check?q=${encodeURIComponent(query)}`);
}

export async function suggestCompanies(query: string): Promise<string[]> {
  if (query.trim().length < 2) return [];
  try {
    const res = await apiFetch<{ suggestions: string[] }>(
      `/blacklist/suggest?q=${encodeURIComponent(query)}`
    );
    return res.suggestions ?? [];
  } catch {
    return [];
  }
}

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  is_admin: boolean;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

export interface Ad {
  id: string;
  userId: string;
  title: string;
  description: string;
  address: string;
  price: number;
  area: number;
  rooms: number;
  propertyType: string;
  photoUrl?: string;
  latitude?: number;
  longitude?: number;
  status: "pending" | "approved" | "rejected";
  adminComment?: string;
  createdAt: string;
  updatedAt: string;
  approvedAt?: string;
}

// ─── Contracts ────────────────────────────────────────────────────────────────

export function generateContract(data: Record<string, unknown>): Promise<Blob> {
  return apiFetch("/contracts/generate-pdf", { method: "POST", body: JSON.stringify(data) });
}

export function getContract(id: string): Promise<Contract> {
  return apiFetch(`/contracts/${id}`);
}

export function getContracts(): Promise<Contract[]> {
  return apiFetch("/contracts");
}

export function sendForSigning(contractId: string): Promise<void> {
  return apiFetch(`/contracts/${contractId}/send-for-signing`, { method: "POST" });
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export function login(payload: { email: string; password: string }): Promise<AuthResponse> {
  return apiFetch("/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export function register(payload: { email: string; password: string; name?: string }): Promise<AuthResponse> {
  return apiFetch("/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    // Ignore backend errors and still clear the client session.
  } finally {
    clearAuthSession();
  }
}

export function getMe(): Promise<AuthUser> {
  return apiFetch("/auth/me");
}

// ─── Ads ──────────────────────────────────────────────────────────────────────

export function createAd(payload: FormData): Promise<{ id: string; status: string }> {
  return apiFetch("/ads", { method: "POST", body: payload });
}

export function listMyAds(): Promise<Ad[]> {
  return apiFetch("/ads/me");
}

export function listPublicAds(): Promise<Ad[]> {
  return apiFetch("/ads");
}

export function getPendingAds(): Promise<Ad[]> {
  return apiFetch("/ads/pending");
}

export function getAdminStats(): Promise<{
  pendingCount: number;
  approvedCount: number;
  rejectedCount: number;
  totalAds: number;
  totalUsers: number;
}> {
  return apiFetch("/ads/admin/stats");
}

export function approveAd(id: string, payload: { admin_comment?: string }): Promise<{ status: string; adId: string }> {
  return apiFetch(`/ads/${id}/approve`, { method: "POST", body: JSON.stringify(payload) });
}

export function rejectAd(id: string, payload: { admin_comment?: string }): Promise<{ status: string; adId: string }> {
  return apiFetch(`/ads/${id}/reject`, { method: "POST", body: JSON.stringify(payload) });
}
