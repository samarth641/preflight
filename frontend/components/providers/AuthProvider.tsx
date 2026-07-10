"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth"
import {
  getFirebaseAuth,
  googleAuthProvider,
  initFirebaseAnalytics,
  isAuthOptional,
  isFirebaseConfigured,
} from "@/lib/firebase"

interface AuthContextValue {
  user: User | null
  loading: boolean
  /** True when login is not required (demo mode or missing Firebase config). */
  authOptional: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const authOptional = isAuthOptional()

  useEffect(() => {
    if (!isFirebaseConfigured()) {
      setLoading(false)
      return
    }

    let unsubscribe: (() => void) | undefined
    try {
      const auth = getFirebaseAuth()
      void initFirebaseAnalytics()
      unsubscribe = onAuthStateChanged(auth, (nextUser) => {
        setUser(nextUser)
        setLoading(false)
      })
    } catch {
      setLoading(false)
    }
    return () => unsubscribe?.()
  }, [])

  const signInWithGoogle = useCallback(async () => {
    const auth = getFirebaseAuth()
    await signInWithPopup(auth, googleAuthProvider)
  }, [])

  const signOut = useCallback(async () => {
    if (!isFirebaseConfigured()) return
    const auth = getFirebaseAuth()
    await firebaseSignOut(auth)
  }, [])

  const value = useMemo(
    () => ({ user, loading, authOptional, signInWithGoogle, signOut }),
    [user, loading, authOptional, signInWithGoogle, signOut]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return ctx
}
