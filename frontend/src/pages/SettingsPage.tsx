export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold">Settings</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl border p-6 space-y-4">
        <div>
          <h3 className="font-semibold">Face Recognition</h3>
          <p className="text-sm text-gray-500 mt-1">Recognition threshold: 0.363 (cosine distance)</p>
          <p className="text-sm text-gray-500">Minimum samples for registration: 10</p>
        </div>
        <div>
          <h3 className="font-semibold">Security</h3>
          <p className="text-sm text-gray-500 mt-1">JWT authentication with HttpOnly cookies</p>
          <p className="text-sm text-gray-500">Passwords hashed with bcrypt</p>
          <p className="text-sm text-gray-500">Face embeddings stored as encrypted binary data</p>
        </div>
        <div>
          <h3 className="font-semibold">Camera</h3>
          <p className="text-sm text-gray-500 mt-1">Requires HTTPS in production or localhost for development</p>
        </div>
      </div>
    </div>
  );
}
