import { Button } from "@/components/ui/button"

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
      <path
        fill="#EA4335"
        d="M12 10.2v3.96h5.6c-.24 1.28-1.68 3.76-5.6 3.76-3.36 0-6.08-2.8-6.08-6.24S8 5.44 11.36 5.44c1.92 0 3.2.8 3.92 1.52l2.72-2.64C16.72 2.32 14.56 1.6 12 1.6 6.72 1.6 2.48 5.84 2.48 11.12S6.72 20.64 12 20.64c6.96 0 9.12-4.88 9.12-7.36 0-.48-.04-.8-.12-1.12H12z"
      />
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
      <path
        fill="#0A66C2"
        d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.95v5.66H9.35V9h3.42v1.56h.05c.48-.9 1.66-1.85 3.42-1.85 3.66 0 4.34 2.41 4.34 5.54v6.2zM5.34 7.43a2.07 2.07 0 1 1 0-4.14 2.07 2.07 0 0 1 0 4.14zM7.12 20.45H3.56V9h3.56v11.45z"
      />
    </svg>
  )
}

export function SocialButtons() {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <Button variant="outline" className="w-full bg-transparent">
        <span className="mr-2 inline-flex h-5 w-5 items-center justify-center">
          <GoogleIcon />
        </span>
        Continue with Google
      </Button>
      <Button variant="outline" className="w-full bg-transparent">
        <span className="mr-2 inline-flex h-5 w-5 items-center justify-center">
          <LinkedInIcon />
        </span>
        Continue with LinkedIn
      </Button>
    </div>
  )
}
