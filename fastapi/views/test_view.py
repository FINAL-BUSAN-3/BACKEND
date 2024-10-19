# views/test_view.py

class TestView:
    @staticmethod
    def render(data: dict):
        """데이터를 보기 좋게 포맷팅"""
        return {"view_message": f"View says: {data['message']}"}