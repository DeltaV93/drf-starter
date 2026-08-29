export interface ValidationError {
  field: string;
  message: string;
}

export const validators = {
  // Trip validators
  isValidTripName: (name: string): string | null => {
    if (!name || name.trim().length === 0) {
      return 'Trip name is required';
    }
    if (name.length > 255) {
      return 'Trip name must be less than 255 characters';
    }
    return null;
  },

  isValidAddress: (address: string): string | null => {
    if (!address || address.trim().length === 0) {
      return 'Address is required';
    }
    if (address.length > 500) {
      return 'Address must be less than 500 characters';
    }
    return null;
  },

  isValidDateTime: (dateTime: string): string | null => {
    if (!dateTime) {
      return 'Date and time are required';
    }
    const date = new Date(dateTime);
    if (isNaN(date.getTime())) {
      return 'Invalid date or time format';
    }
    return null;
  },

  isValidTimeRange: (startTime: string, endTime: string): string | null => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    if (end <= start) {
      return 'End time must be after start time';
    }
    return null;
  },

  // Document validators
  isValidFileName: (fileName: string): string | null => {
    if (!fileName || fileName.trim().length === 0) {
      return 'File name is required';
    }
    if (fileName.length > 255) {
      return 'File name must be less than 255 characters';
    }
    return null;
  },

  isValidCategory: (category: string): string | null => {
    const validCategories = [
      'receipts',
      'mortgage',
      'offer_letter',
      'inspection',
      'appraisal',
      'title',
      'other',
    ];
    if (!validCategories.includes(category)) {
      return 'Invalid document category';
    }
    return null;
  },

  // Share validators
  isValidPassword: (password: string): string | null => {
    if (password && password.length > 255) {
      return 'Password must be less than 255 characters';
    }
    return null;
  },

  isValidExpirationDays: (days: string): string | null => {
    if (!days) return null; // Optional field
    const num = parseInt(days, 10);
    if (isNaN(num) || num < 1 || num > 365) {
      return 'Expiration days must be between 1 and 365';
    }
    return null;
  },
};

// Validate a single field
export function validateField(field: string, value: string): string | null {
  const validationMap: Record<string, (v: string) => string | null> = {
    tripName: validators.isValidTripName,
    address: validators.isValidAddress,
    startTime: validators.isValidDateTime,
    endTime: validators.isValidDateTime,
    fileName: validators.isValidFileName,
    password: validators.isValidPassword,
    expirationDays: validators.isValidExpirationDays,
  };

  const validator = validationMap[field];
  return validator ? validator(value) : null;
}

// Validate multiple fields at once
export function validateFields(fields: Record<string, string>): ValidationError[] {
  const errors: ValidationError[] = [];

  Object.entries(fields).forEach(([field, value]) => {
    const error = validateField(field, value);
    if (error) {
      errors.push({ field, message: error });
    }
  });

  return errors;
}

// Check if start and end times are valid
export function validateTripTimes(
  startTime: string,
  endTime: string
): ValidationError[] {
  const errors: ValidationError[] = [];

  const startError = validateField('startTime', startTime);
  if (startError) {
    errors.push({ field: 'startTime', message: startError });
  }

  const endError = validateField('endTime', endTime);
  if (endError) {
    errors.push({ field: 'endTime', message: endError });
  }

  if (!startError && !endError) {
    const timeRangeError = validators.isValidTimeRange(startTime, endTime);
    if (timeRangeError) {
      errors.push({ field: 'endTime', message: timeRangeError });
    }
  }

  return errors;
}
