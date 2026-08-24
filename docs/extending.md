# Extending the template

Recipes for the things you will actually do. Each follows the conventions in
[CLAUDE.md](../CLAUDE.md), which CI enforces — a step skipped here is usually a
step that fails the build.

Start with [architecture.md](architecture.md) if you have not read it: several
of these steps only make sense once you know why the flags are independent.

---

## Add an endpoint to an existing app

Four files, in this order.

### 1. A serializer for the request, and one for the response

```python
# apps/widgets/serializers.py
class WidgetCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ['id', 'name', 'created_at']
        read_only_fields = fields
```

Both, not one. The response shape is usually not the request shape, and saying
so is what lets the schema describe either honestly.

### 2. The view

```python
class WidgetListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List your widgets',
        responses={200: WidgetSerializer(many=True)},
    )
    def get(self, request):
        widgets = Widget.objects.filter(user=request.user)
        return api_response(
            data=WidgetSerializer(widgets, many=True).data,
            message='Widgets retrieved.',
        )

    @extend_schema(
        summary='Create a widget',
        request=WidgetCreateSerializer,
        responses={201: WidgetSerializer},
    )
    def post(self, request):
        serializer = WidgetCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Could not create the widget.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        ...
```

Non-negotiable, because CI checks each one:

- **`APIView`, never Django's `View`** — a plain `View` cannot render a DRF
  `Response`.
- **`api_response` for every return**, so the envelope is uniform.
- **`@extend_schema` with both `request=` and `responses=`.** A `summary` alone
  leaves drf-spectacular guessing, and it cannot guess for a plain `APIView`.
  `make check` and CI both run `spectacular --fail-on-warn`, so an undocumented
  view fails the build. Use `responses={200: None}` for a genuinely empty body.
- **Filter by `request.user`.** `DEFAULT_PERMISSION_CLASSES` gets you
  authentication, not authorisation.

### 3. The route

```python
# apps/widgets/urls.py
urlpatterns = [
    path('widgets/', WidgetListCreateView.as_view(), name='widget_list'),
]
```

**End it in a slash.** Django's `APPEND_SLASH` turns a slashless POST into a
redirect that loses the body — the request arrives with no data and the error
makes no sense.

### 4. The frontend path

```ts
// website/src/lib/routes.ts
widgets: {
  list: () => join(BASE_URL, 'widgets/'),
},
```

`routes.ts` is the only place the SPA names a backend path, and it preserves
the trailing slash for the same reason.

### If the endpoint takes an email address

Answer **identically whether or not the account exists**. Same status, same
message, same timing characteristics. Otherwise the endpoint is an account
enumeration oracle, and every existing one in this project is careful about it.

---

## Add a whole feature behind a flag

The pattern all seven optional features follow. The rule that makes it work:
**your new app must not hold a foreign key into another optional app.** Scope
every model to `settings.AUTH_USER_MODEL`.

### 1. Create the app

```bash
# startapp will not create the destination itself.
mkdir apps/widgets && .venv/bin/python manage.py startapp widgets apps/widgets
```

Set the label in `apps/widgets/apps.py`:

```python
class WidgetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.widgets'
```

### 2. Declare the flag

```python
# template/settings/base.py, with the others around line 105
# What it is, and why it is off by default.
WIDGETS_ENABLED = env_bool('WIDGETS_ENABLED', default=False)

if WIDGETS_ENABLED:
    INSTALLED_APPS.append('apps.widgets')
```

### 3. Gate the URLs

```python
# template/urls.py
if settings.WIDGETS_ENABLED:
    api_v1_patterns.append(path('', include('apps.widgets.urls')))
```

### 4. Turn it on for the test suite

```python
# template/settings/testing.py -- BEFORE `from .base import *`
os.environ.setdefault('WIDGETS_ENABLED', 'true')
```

The ordering matters: `base.py` reads the flag while it is being imported, so
setting it afterwards has no effect.

### 5. Skip the app's tests when the flag is off

```python
# apps/widgets/tests/conftest.py
collect_ignore_glob = [] if settings.WIDGETS_ENABLED else ['test_*.py']
```

Without this the suite fails at *collection* with the flag off — the models
cannot be imported when the app is not installed.

### 6. Add it to the CI matrix

```yaml
# .github/workflows/ci.yml
FLAGS="STRIPE_ENABLED ... UPLOADS_ENABLED WIDGETS_ENABLED"
```

That is what proves the feature is genuinely independent: the suite runs with
it off, and with everything else on and it off.

### 7. Add the frontend twin

`VITE_WIDGETS_ENABLED` in four places:

- `website/.env.example`
- `website/src/vite-env.d.ts` (the `ImportMetaEnv` interface)
- `Dockerfile` — both the `ARG` and the `ENV` line, because Vite inlines it at
  build time
- the component that should disappear when the feature is off

`apps/core/tests/test_env_documented.py` fails if a backend flag has no `VITE_`
twin. Six features once shipped backend-only; that test is why it cannot happen
quietly again.

### 8. Document it

- `.env.example` — the variable, with a comment
- `docs/configuration.md` — a table row, or the drift test fails
- `README.md` — a section, including **how to delete the feature outright**

### 9. Migrations

```bash
make migrations   # then commit the result
```

`apps/*/migrations/` must never go back into `.gitignore`. With a custom
`AUTH_USER_MODEL`, a fresh clone cannot `migrate` without them — that was the
single biggest reason this template did not work.

---

## Add a model field

```bash
make migrations && make check
```

`make check` runs `makemigrations --check --dry-run`, so a forgotten migration
fails locally before it fails in CI. Commit the migration in the same change as
the model.

If the field is user data, add it to the GDPR export in `utils/gdpr_utils.py`
and to the erasure path. Portability and erasure are the same obligation from
two directions, and a field in one but not the other is a bug in whichever is
missing.

---

## Add a page to the SPA

```tsx
// website/src/components/pages/WidgetsPage.tsx
export default function WidgetsPage() {
  const { t } = useTranslation();
  const [widgets, setWidgets] = useState<Widget[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const data = await apiData<Widget[]>({ url: routes.api.widgets.list() });
      if (!cancelled) setWidgets(data ?? []);
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  ...
}
```

Then register the route in `App.tsx`, lazily, gated by the flag:

```tsx
const WidgetsPage = lazy(() => import('./components/pages/WidgetsPage'));
const WIDGETS_ENABLED = import.meta.env.VITE_WIDGETS_ENABLED === 'true';

{WIDGETS_ENABLED && (
  <Route path="/widgets" element={<ProtectedRoute><WidgetsPage /></ProtectedRoute>} />
)}
```

Things the linter will hold you to:

- **The inline-async-IIFE with a cancellation guard** is the pattern here, not a
  bare `setState` in an effect. The React Compiler rule `set-state-in-effect`
  rejects the latter, and it is right to: an unguarded effect writes state after
  the component has unmounted.
- **Derive, do not store.** `loading` is `widgets === null`, not a second piece
  of state that can disagree with the first.
- **No colours.** Use theme keys (`color="text.secondary"`, `bgcolor="background.paper"`)
  so the page follows the brand and both colour schemes. See
  [Theming](../README.md#theming).
- **No hand-set `X-CSRFToken`.** `src/lib/api.ts` is the only place that touches
  CSRF.
- ESLint runs with `--max-warnings 0`. Fix the code rather than disabling the
  rule.

Add user-visible strings to `website/src/locales/en.json` **and** `es.json` — a
missing key renders as the key itself.

---

## Add a background task

```python
# apps/widgets/tasks.py
@shared_task
def rebuild_widget_index(user_id: int) -> None: ...
```

Pass **IDs, not objects**. A serialised model instance is a snapshot that is
already stale by the time the worker picks it up, and it fails outright if the
row was deleted in between.

Whether it runs in-process or on a worker follows `EMAIL_ASYNC` for email; a
task of your own should decide deliberately and say so in `.env.example`. Under
test, `CELERY_TASK_ALWAYS_EAGER` makes tasks run synchronously and propagate
failures — a task that only works asynchronously will look fine and never be
exercised.

If the task grows unbounded output, add a retention command next to
`prune_audit_log` rather than letting the table grow forever.

---

## Add an audited action

```python
from apps.core.audit import AuditAction, audit

audit(
    AuditAction.WIDGET_DELETED,
    actor=request.user,
    request=request,
    target=widget.name,
    widget_id=widget.pk,
)
```

`apps/core/audit.py` lives in an always-installed app and **no-ops when
`AUDIT_LOG_ENABLED` is off**, so call sites need no flag check and the audit app
stays independent of everything that writes to it.

Metadata is allow-listed per action. Never pass `request.data` — a password or a
card number would land in an append-only table that by design cannot be edited.

Check what you pass: an audit call that reads the wrong key records an empty
target on every event, and nothing fails.

---

## Add a locale

1. `website/src/locales/fr.json`, with every key from `en.json`
2. Register it in `website/src/i18n.ts`
3. For backend strings, `django-admin makemessages -l fr`, translate, then
   `compilemessages`

`LocaleMiddleware` is already in the stack.

The product name is **not** in the locale files — it comes from
`brand.ts`, so a rebrand does not mean editing one file per language. If yours
genuinely is translated, put `appName` back in the locales and read it through
`t('appName')`.

---

## Remove a feature you do not want

Every optional app is designed to come out in one commit. The README has an
exact "Removing it" block per feature; the shape is always:

```bash
git rm -r apps/widgets website/src/components/pages/WidgetsPage.tsx
```

then drop the `WIDGETS_ENABLED` branches from `template/settings/base.py` and
`template/urls.py`, the route from `website/src/App.tsx`, and the flag from the
CI matrix and both `.env.example` files.

Nothing else holds a foreign key into it, so nothing else needs touching. Run
the suite afterwards — the drift test will tell you if a variable is still
documented that nothing reads.

---

## Before you push

```bash
make lint     # ruff + ruff format + eslint + tsc
make test     # pytest + vitest
make check    # django checks, deploy checklist, missing migrations, OpenAPI schema
```

`make check` runs the schema generator because CI does. A new view without a
declared request and response passes every other target and only turns red on
the pull request — which is exactly how eight features' worth of schema errors
accumulated once.

For a change to an optional feature, also run it with the flag off:

```bash
WIDGETS_ENABLED=false .venv/bin/python -m pytest -q
```

A feature that only works enabled is half a feature.
