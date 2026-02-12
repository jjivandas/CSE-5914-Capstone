import { useEffect, useRef } from "react";

export function useAutoScroll(dependencies: unknown[]) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [dependencies]);

  return bottomRef;
}
