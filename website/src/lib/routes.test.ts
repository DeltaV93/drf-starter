import { describe, expect, it } from 'vitest';

import { routes } from './routes';

describe('api route building', () => {
  it('joins segments with exactly one slash', () => {
    // The old apiJoin used a bare endpoints.join('/'), so a base URL with a
    // trailing slash produced '//login/'.
    expect(routes.api.auth.login()).toBe('/api/v1/auth/login/');
    expect(routes.api.users.me()).toBe('/api/v1/users/me/');
  });

  it('interpolates path parameters', () => {
    expect(routes.api.auth.passwordResetValidate('MQ', 'tok-123')).toBe(
      '/api/v1/auth/password-reset/MQ/tok-123/',
    );
    expect(routes.api.billing.subscribe('price_abc')).toBe(
      '/api/v1/billing/subscribe/price_abc/',
    );
    expect(routes.api.billing.addAddon(7)).toBe('/api/v1/billing/add-addon/7/');
  });

  it('never emits a double slash', () => {
    const urls = [
      routes.api.health(),
      routes.api.auth.csrf(),
      routes.api.auth.register(),
      routes.api.auth.passwordResetConfirm(),
      routes.api.billing.plans(),
    ];

    for (const url of urls) {
      expect(url).not.toMatch(/\/\//);
    }
  });
});

describe('app routes', () => {
  it('produces router patterns by default and real paths when given values', () => {
    expect(routes.app.confirmPassword()).toBe('/confirm-password/:uid/:token');
    expect(routes.app.confirmPassword('MQ', 'tok')).toBe('/confirm-password/MQ/tok');
    expect(routes.app.verifyEmail()).toBe('/verify-email/:uid/:token');
  });
});
