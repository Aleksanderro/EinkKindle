# Architecture

The server-side data flow is:

```text
Open-Meteo
    -> weather layer
    -> normalized domain model
    -> renderer
    -> weather.png
    -> read-only HTTP
    -> Kindle
```

The weather layer owns provider integration and converts provider data into a normalized domain
model. The renderer consumes only that normalized model and must not depend directly on the
provider's JSON response.

The renderer produces the complete display image. The HTTP layer exposes generated output as a
minimal, read-only runtime surface. The Kindle only downloads and displays the prepared image.
