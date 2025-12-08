/**
 * useAuth hook: provides auth state and methods
 * Handles login, logout, and auth status
 */

'use client';

import { useContext, createContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { 
    setAuthToken, 
    getAuthToken, 
    clearAuthToken, 
    isAuthenticated as checkAuth 
} from './auth';

interface User {
    id: number;
    email: string;
    is_verified: boolean;
}

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Check auth state on mount
    useEffect(() => {
        if (checkAuth()) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setIsAuthenticated(true);
            // Optionally fetch user profile from /me endpoint (not yet implemented)
        }
        setIsLoading(false);
    }, []);

    const login = async (email: string, password: string) => {
        const apiBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001').replace(/\/$/, '');
        const res = await fetch(`${apiBase}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
            credentials: 'include',
        });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data?.detail || 'Login failed');
        }
        const data = await res.json();
        setAuthToken(data.access_token);
        setIsAuthenticated(true);
    };

    const logout = () => {
        clearAuthToken();
        setUser(null);
        setIsAuthenticated(false);
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
}
