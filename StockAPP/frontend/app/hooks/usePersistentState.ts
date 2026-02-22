/**
 * 持久化状态 Hook
 * ===============
 * 使用 localStorage 保存状态，页面刷新或切换后自动恢复
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_PREFIX = 'stockapp_';

export function usePersistentState<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const storageKey = `${STORAGE_PREFIX}${key}`;

  const [state, setState] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored !== null) {
        return JSON.parse(stored) as T;
      }
    } catch (error) {
      console.warn(`Failed to load state from localStorage: ${key}`, error);
    }
    return defaultValue;
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch (error) {
      console.warn(`Failed to save state to localStorage: ${key}`, error);
    }
  }, [storageKey, state]);

  return [state, setState];
}

export function usePersistentCallback<T extends (...args: any[]) => any>(
  key: string,
  callback: T
): T {
  return useCallback(
    ((...args: Parameters<T>) => {
      const result = callback(...args);
      return result;
    }) as T,
    [callback]
  );
}

export function clearPersistentState(pattern?: string): void {
  const keys = Object.keys(localStorage);
  const prefix = pattern ? `${STORAGE_PREFIX}${pattern}` : STORAGE_PREFIX;
  
  keys.forEach(key => {
    if (key.startsWith(prefix)) {
      localStorage.removeItem(key);
    }
  });
}

export function getPersistentState<T>(key: string, defaultValue: T): T {
  const storageKey = `${STORAGE_PREFIX}${key}`;
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored !== null) {
      return JSON.parse(stored) as T;
    }
  } catch (error) {
    console.warn(`Failed to load state from localStorage: ${key}`, error);
  }
  return defaultValue;
}

export function setPersistentState<T>(key: string, value: T): void {
  const storageKey = `${STORAGE_PREFIX}${key}`;
  try {
    localStorage.setItem(storageKey, JSON.stringify(value));
  } catch (error) {
    console.warn(`Failed to save state to localStorage: ${key}`, error);
  }
}
