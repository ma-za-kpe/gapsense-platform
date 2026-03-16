    async def _handle_image_analyze(self, task: WorkerTask) -> None:
        """Delegate entirely to ImageAnalysisOrchestrator."""
        from gapsense.engagement.image_analysis_orchestrator import ImageAnalysisOrchestrator

        orchestrator = ImageAnalysisOrchestrator(
            db=self._db,
            ai_client=self._ai_client,
            media_service=self._media_service,
            guard_service=self._guard_service,
            prompt_service=self._prompt_service,
            worker_service=self,
        )
        await orchestrator.run(task.payload)
