"use client";
import React, { createContext, useContext, useEffect, useState } from "react";

type Lang = "en" | "hi";

// Bilingual dictionary. Structure is ready to extend to more languages.
const DICT: Record<string, { en: string; hi: string }> = {
  app_name: { en: "UNNATI", hi: "उन्नति" },
  tagline: { en: "Scholarship & Fellowship Portal", hi: "छात्रवृत्ति एवं फ़ेलोशिप पोर्टल" },
  ministry: { en: "Ministry of Tribal Affairs", hi: "जनजातीय कार्य मंत्रालय" },
  govt_india: { en: "Government of India", hi: "भारत सरकार" },
  login: { en: "Login", hi: "लॉगिन" },
  logout: { en: "Logout", hi: "लॉगआउट" },
  email: { en: "Email", hi: "ईमेल" },
  password: { en: "Password", hi: "पासवर्ड" },
  demo_logins: { en: "Demo logins", hi: "डेमो लॉगिन" },
  dashboard: { en: "Dashboard", hi: "डैशबोर्ड" },
  schemes: { en: "Schemes", hi: "योजनाएँ" },
  eligible_schemes: { en: "Schemes you may be eligible for", hi: "योजनाएँ जिनके लिए आप पात्र हो सकते हैं" },
  my_applications: { en: "My Applications", hi: "मेरे आवेदन" },
  apply: { en: "Apply", hi: "आवेदन करें" },
  eligible: { en: "Eligible", hi: "पात्र" },
  not_eligible: { en: "Not eligible", hi: "अपात्र" },
  documents: { en: "Documents", hi: "दस्तावेज़" },
  upload: { en: "Upload", hi: "अपलोड" },
  submit: { en: "Submit", hi: "जमा करें" },
  save_draft: { en: "Save draft", hi: "ड्राफ्ट सहेजें" },
  status: { en: "Status", hi: "स्थिति" },
  tracker: { en: "Application Tracker", hi: "आवेदन ट्रैकर" },
  deficiencies: { en: "Deficiencies", hi: "कमियाँ" },
  notifications: { en: "Notifications", hi: "सूचनाएँ" },
  resubmit: { en: "Resubmit", hi: "पुनः जमा करें" },
  scrutiny_queue: { en: "Scrutiny Queue", hi: "जाँच सूची" },
  review: { en: "Review", hi: "समीक्षा" },
  verify: { en: "Verify", hi: "सत्यापित करें" },
  raise_deficiency: { en: "Raise Deficiency", hi: "कमी दर्ज करें" },
  reject: { en: "Reject", hi: "अस्वीकार करें" },
  override: { en: "Override", hi: "अधिरोहण" },
  ai_flags: { en: "AI Flags", hi: "एआई संकेत" },
  risk_score: { en: "Risk score", hi: "जोखिम स्कोर" },
  merit_list: { en: "Merit List", hi: "मेरिट सूची" },
  generate_merit: { en: "Generate Merit List", hi: "मेरिट सूची बनाएँ" },
  publish: { en: "Publish Results", hi: "परिणाम प्रकाशित करें" },
  audit_log: { en: "Audit Log", hi: "ऑडिट लॉग" },
  scheme_config: { en: "Scheme Configuration", hi: "योजना विन्यास" },
  sample_notice: {
    en: "Sample values — to be updated per official MoTA guidelines",
    hi: "नमूना मान — आधिकारिक दिशानिर्देशों के अनुसार अद्यतन किए जाने हैं",
  },
  eligibility_rules: { en: "Eligibility Rules", hi: "पात्रता नियम" },
  required_documents: { en: "Required Documents", hi: "आवश्यक दस्तावेज़" },
  merit_criteria: { en: "Merit Criteria", hi: "मेरिट मानदंड" },
};

const I18nCtx = createContext<{ lang: Lang; t: (k: string) => string; toggle: () => void }>({
  lang: "en", t: (k) => k, toggle: () => {},
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  useEffect(() => {
    try {
      const saved = localStorage.getItem("lang") as Lang | null;
      if (saved) setLang(saved);
    } catch {}
  }, []);
  const toggle = () => {
    setLang((l) => {
      const next = l === "en" ? "hi" : "en";
      try { localStorage.setItem("lang", next); } catch {}
      return next;
    });
  };
  const t = (k: string) => DICT[k]?.[lang] ?? k;
  return <I18nCtx.Provider value={{ lang, t, toggle }}>{children}</I18nCtx.Provider>;
}

export const useI18n = () => useContext(I18nCtx);
