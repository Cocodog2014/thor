// RealTimeProvider is parked; real-time hooks now live in src/realtime.
// Keeping a stub to avoid import errors if referenced elsewhere.
const RealTimeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => <>{children}</>;

export { RealTimeProvider };
