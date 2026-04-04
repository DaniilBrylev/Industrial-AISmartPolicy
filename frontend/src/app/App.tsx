import { Layout } from "@/app/Layout";
import { DashboardPage } from "@/pages/DashboardPage";
import { DepartmentsPage } from "@/pages/DepartmentsPage";
import { PoliciesPage } from "@/pages/PoliciesPage";
import { QuestionnaireDetailPage } from "@/pages/QuestionnaireDetailPage";
import { QuestionnairesPage } from "@/pages/QuestionnairesPage";
import { VersionsHistoryPage } from "@/pages/VersionsHistoryPage";
import { Route, Routes } from "react-router-dom";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="departments" element={<DepartmentsPage />} />
        <Route path="questionnaires" element={<QuestionnairesPage />} />
        <Route path="questionnaires/:id" element={<QuestionnaireDetailPage />} />
        <Route path="policies" element={<PoliciesPage />} />
        <Route path="versions" element={<VersionsHistoryPage />} />
      </Route>
    </Routes>
  );
}
