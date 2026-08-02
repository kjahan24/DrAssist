import Link from "next/link";
import { Github, Linkedin, Stethoscope, Twitter } from "lucide-react";

import { footerLinks } from "@/config/marketing-nav";
import { siteConfig } from "@/config/site";

export function MarketingFooter() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="container grid gap-10 py-12 md:grid-cols-6">
        <div className="md:col-span-2">
          <Link
            href="/"
            className="flex items-center gap-2 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`${siteConfig.name} home`}
          >
            <Stethoscope className="size-6 text-primary" aria-hidden="true" />
            <span>{siteConfig.name}</span>
          </Link>
          <p className="mt-3 max-w-xs text-sm text-muted-foreground">{siteConfig.description}</p>
          <div className="mt-4 flex gap-3">
            <Link
              href={siteConfig.links.twitter}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Twitter"
              target="_blank"
              rel="noreferrer"
            >
              <Twitter className="size-4" />
            </Link>
            <Link
              href={siteConfig.links.linkedin}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="LinkedIn"
              target="_blank"
              rel="noreferrer"
            >
              <Linkedin className="size-4" />
            </Link>
            <Link
              href={siteConfig.links.github}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="GitHub"
              target="_blank"
              rel="noreferrer"
            >
              <Github className="size-4" />
            </Link>
          </div>
        </div>
        {footerLinks.map((group) => (
          <div key={group.title}>
            <h3 className="text-sm font-semibold">{group.title}</h3>
            <ul className="mt-3 space-y-2">
              {group.links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t">
        <div className="container flex flex-col items-center justify-between gap-2 py-6 text-sm text-muted-foreground sm:flex-row">
          <p>
            © {new Date().getFullYear()} {siteConfig.name}. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
