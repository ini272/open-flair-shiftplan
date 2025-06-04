export const translations = {
  // Navigation & General
  dashboard: 'Dashboard',
  logout: 'Abmelden',
  login: 'Anmelden',
  close: 'Schließen',
  save: 'Speichern',
  cancel: 'Abbrechen',
  delete: 'Löschen',
  edit: 'Bearbeiten',
  
  // Time & Dates
  time: 'Zeit',
  date: 'Datum',
  
  // Days of week
  days: {
    monday: 'Montag',
    tuesday: 'Dienstag',
    wednesday: 'Mittwoch', 
    thursday: 'Donnerstag',
    friday: 'Freitag',
    saturday: 'Samstag',
    sunday: 'Sonntag',
    // Short versions for grid headers
    mon: 'Mo',
    tue: 'Di',
    wed: 'Mi', 
    thu: 'Do',
    fri: 'Fr',
    sat: 'Sa',
    sun: 'So'
  },
  
  // Shifts
  shifts: {
    myShifts: 'Meine Schichten',
    availableShifts: 'Verfügbare Schichten',
    coordinatorView: 'Koordinator Ansicht',
    shiftDetails: 'Schicht Details',
    capacity: 'Kapazität',
    description: 'Beschreibung',
    noDescription: 'Keine Beschreibung',
    assignedUsers: 'Zugewiesene Benutzer',
    assignedGroups: 'Zugewiesene Gruppen',
    noUsers: 'Keine Benutzer zugewiesen',
    noGroups: 'Keine Gruppen zugewiesen',
    available: 'Verfügbar',
    notAvailable: 'Nicht verfügbar',
    signedUp: 'Du bist für diese Schicht angemeldet.',
    notSignedUp: 'Du bist nicht für diese Schicht angemeldet.',
    clickToToggle: 'Klicke auf eine Schicht um deine Verfügbarkeit zu ändern (grün = verfügbar, rot = nicht verfügbar).',
    generatePlan: 'Plan generieren',
    generating: 'Generiere...',
    planGenerated: 'Plan wurde erfolgreich generiert!',
    planGenerationFailed: 'Plan-Generierung fehlgeschlagen.',
    optedInSuccess: 'Erfolgreich für Schicht angemeldet',
    optedOutSuccess: 'Erfolgreich von Schicht abgemeldet', 
    updateFailed: 'Schicht-Aktualisierung fehlgeschlagen. Bitte versuche es erneut.'
  },
  
  // Festival
  festival: {
    name: 'Open Flair Festival',
    year: '2025',
    dates: '6. - 10. August 2025',
    location: 'Eschwege, Deutschland',
    timetable: 'Festival Zeitplan ansehen',
    crewDashboard: 'Open Flair Festival Crew Dashboard',
    shiftPlanner: 'Schichtplaner 2025'
  },
  
  // Account & Users
  account: {
    welcome: 'Willkommen',
    selectUser: 'Benutzer auswählen',
    newUser: 'Neuer Benutzer',
    existingUser: 'Bestehender Benutzer',
    createAccount: 'Erstelle dein Konto',
    welcomeBack: 'Willkommen zurück',
    accountAccess: 'Konto Zugang',
    username: 'Dein Name',
    email: 'E-Mail Adresse',
    group: 'Gruppenname',
    yourGroup: 'Du bist Teil der Gruppe',
    workPreference: 'Wie möchtest du arbeiten?',
    workAlone: 'Ich arbeite alleine',
    workInGroup: 'Ich arbeite in einer Gruppe',
    createAccountButton: 'Konto erstellen',
    creatingAccount: 'Erstelle Konto...',
    continue: 'Weiter',
    searchingAccount: 'Suche Konto...',
    emailHelper: 'Du verwendest diese E-Mail beim nächsten Mal zum Anmelden',
    groupHelper: 'Gib eine bestehende Gruppe ein oder erstelle eine neue'
  },
  
  // Authentication
  auth: {
    login: 'Anmelden',
    accessToken: 'Zugangs-Token',
    enterToken: 'Bitte gib einen Token ein',
    invalidToken: 'Ungültiger Token. Bitte versuche es erneut.',
    checking: 'Wird überprüft...',
    tokenPlaceholder: 'Gib deinen Zugangs-Token ein'
  },
  
  // Messages & Status
  messages: {
    success: 'Erfolgreich',
    error: 'Fehler',
    loading: 'Lädt...',
    noData: 'Keine Daten verfügbar',
    tryAgain: 'Bitte versuche es erneut'
  },
  
  // Coordinator
  coordinator: {
    dashboard: 'Koordinator Dashboard',
    totalShifts: 'Schichten Gesamt',
    availableUsers: 'Verfügbare Benutzer',
    shiftCoverage: 'Schicht Abdeckung',
    understaffedShifts: 'Unterbesetzte Schichten',
    shiftAssignments: 'Schicht Zuweisungen',
    lastGenerated: 'Zuletzt generiert',
    clearExisting: 'Bestehende Zuweisungen löschen',
    useGroups: 'Gruppen-Zuweisungen verwenden',
    generatePlan: 'Plan generieren',
    generating: 'Generiere...',
    planGenerated: 'Plan wurde erfolgreich generiert',
    assignmentsGenerated: 'Zuweisungen erfolgreich generiert',
    planGenerationFailed: 'Plan-Generierung fehlgeschlagen'
  },
  
  // Grid
  grid: {
    timeSlot: 'Zeitfenster',
    time: 'Zeit',
    noShifts: 'Keine Schichten',
    noAssignments: 'Keine Zuweisungen',
    empty: 'Leer',
    understaffed: 'Unterbesetzt',
    partial: 'Teilweise besetzt',
    fullyStaffed: 'Vollständig besetzt',
    overstaffed: 'Überbesetzt',
    noShiftsAvailable: 'Keine Schichten verfügbar'
  }
};