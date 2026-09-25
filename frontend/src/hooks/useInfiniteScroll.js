import { useCallback, useEffect, useRef } from "react";

export default function useInfiniteScroll(callbackParam, isActive = true) {
  const observerRef = useRef(null);

  const callback = useCallback(
    (entries) => {
      if (entries.length === 0) {
        return;
      }

      if (entries[0].isIntersecting && isActive) {
        callbackParam();
      }
    },
    [callbackParam, isActive],
  );

  const infiniteScrollRef = useCallback(
    (node) => {
      if (!node) {
        return;
      }

      observerRef.current?.disconnect();

      observerRef.current = new IntersectionObserver(callback);
      observerRef.current.observe(node);
    },
    [callback],
  );

  useEffect(() => {
    return () => observerRef.current?.disconnect();
  }, []);

  return infiniteScrollRef;
}
