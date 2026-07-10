import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app"
import { getAuth, GoogleAuthProvider, type Auth } from "firebase/auth"
import { getAnalytics, isSupported, type Analytics } from "firebase/analytics"

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
}

/** Hackathon / Docker demo: skip login when set (Compose defaults to true). */
export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true"
}

export function isFirebaseConfigured(): boolean {
  return Boolean(
    firebaseConfig.apiKey && firebaseConfig.authDomain && firebaseConfig.projectId
  )
}

/** Guest access when demo mode is on or Firebase keys are missing. */
export function isAuthOptional(): boolean {
  return isDemoMode() || !isFirebaseConfigured()
}

function assertConfig(): void {
  if (!isFirebaseConfigured()) {
    throw new Error(
      "Firebase is not configured. Copy frontend/.env.local.example to .env.local and set NEXT_PUBLIC_FIREBASE_* variables."
    )
  }
}

export function getFirebaseApp(): FirebaseApp {
  assertConfig()
  return getApps().length ? getApp() : initializeApp(firebaseConfig)
}

export function getFirebaseAuth(): Auth {
  return getAuth(getFirebaseApp())
}

export const googleAuthProvider = new GoogleAuthProvider()
googleAuthProvider.setCustomParameters({ prompt: "select_account" })

let analyticsInit: Promise<Analytics | null> | null = null

export function initFirebaseAnalytics(): Promise<Analytics | null> {
  if (typeof window === "undefined") return Promise.resolve(null)
  if (!analyticsInit) {
    analyticsInit = isSupported().then((ok) => (ok ? getAnalytics(getFirebaseApp()) : null))
  }
  return analyticsInit
}
