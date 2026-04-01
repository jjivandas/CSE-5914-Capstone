# Frontend Development Rules

## 1. File Structure & Organization
- **Separation of Concerns:** Constants (`constants/`), Utilities (`utils/`), and Types (`types/`) **MUST** exist in isolated files. Never define these inside component files.
- **Component Organization:** Group by feature or type (e.g., `features/Auth`, `components/ui/Button`). Co-locate related styles/tests.
- **Barrels:** Use `index.ts` for clean public exports, but avoid circular dependencies.

## 2. Function Architecture
- **Single Responsibility:** One function performs exactly one task.
- **Length Constraint:** Strictly target <15 lines per function.
- **Extraction:** Never inline complex logic or conditionals. Extract to named helper functions immediately.
- **Naming:** Precise verb-noun naming (e.g., `formatCurrency`, `handleSubmit`). Function name must fully describe its operation.

## 3. Core Principles
- **DRY (Don't Repeat Yourself):** Zero code duplication. Abstract patterns into custom hooks or utilities instantly.
- **OOD (Object-Oriented Design):** Encapsulate data and behavior. Favor composition.
- **SOLID:**
  - **SRP:** Components/Hooks manage one concern only.
  - **OCP:** Extend behavior via props/composition; do not modify stable source.
  - **LSP:** Derived components must be substitutable for base components.
  - **ISP:** Define narrow, specific interfaces for props. Avoid "God objects".
  - **DIP:** Depend on abstractions (Context/Hooks) rather than concrete implementations.

## 4. React Perfection
- **Logic Separation:** **ALL** business logic/state in custom hooks. Components = pure UI (View layer).
- **State Management:**
  - `useState`: Local UI state only.
  - `useReducer`: Complex local state transitions.
  - Global: Context or Zustand (prefer atomic updates). **NO** prop drilling > 2 levels.
- **Hooks:** Create custom hooks (e.g., `useFetch`, `useAuth`) for ALL reusable logic.
- **Props:** Strict TypeScript interfaces. No `any`. Explicitly define inputs. Destructure in signature.
- **Performance:**
  - `React.memo`: Wrap pure functional components.
  - `useMemo`/`useCallback`: Mandatory for referential equality on objects/functions passed as props.
  - `useEffect`: **NEVER** for derived state. Calculate in render or `useMemo`.
- **Handlers:** Named handlers only. No anonymous functions in JSX.
- **Error Handling:** Wrap feature roots in Error Boundaries. Fail gracefully.

## 5. Mantine Usage
- **Primitives:** Use Mantine layout components (`Stack`, `Group`, `Box`) instead of `div`.
- **Theming:** Strictly use `theme` tokens (colors, spacing). **NO** hardcoded hex codes or pixel values.
- **Styles:** Utilize Mantine style props (`mt`, `p`, `c`) for atomic styling.
- **Consistency:** Wrap Mantine primitives in domain components for repetitive UI patterns.

## 6. Review Standards
- Functions > 15 lines = Reject.
- Inline logic/constants/types = Reject.
- Hardcoded styles/values = Reject.
- Missing `useCallback`/`useMemo` on props = Reject.
- "God components" (>150 lines) = Reject.